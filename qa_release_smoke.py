"""Offline smoke tests for the release-specific API and privacy changes.

Use a disposable SQLite database; production uses PostgreSQL. This test
adapts PostgreSQL JSONB to SQLite *only in the test app*.
Run after installing requirements:
    python -m qa_release_smoke
"""
import os
import unittest
from unittest.mock import patch

os.environ['APP_ENV'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app.config import Config
Config.SQLALCHEMY_ENGINE_OPTIONS = {}

from app import create_app
from app.extensions import db
from app.models import Product, User, Person
from flask_jwt_extended import create_access_token
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


class ReleaseReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        for table in db.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSON()
        db.create_all()
        cls.client = cls.app.test_client()
        seller = User(email='private-seller@example.test', password_hash='hash',
                      role=User.ROLE_UMKM, is_active=True, is_email_verified=True)
        db.session.add(seller)
        db.session.flush()
        db.session.add(Product(seller_user_id=seller.id, name='Produk uji',
                               description='Contoh', price=10000, contact='0821000000',
                               is_active=True, image_urls=[]))
        db.session.add(Product(seller_user_id=seller.id, name='Produk tak aktif',
                               description='Contoh', price=10000, is_active=False,
                               image_urls=[]))
        db.session.commit()
        cls.seller_id = seller.id
        cls.seller_token = create_access_token(identity=str(seller.id))

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def test_guest_browses_public_features(self):
        for url in ('/api/products', '/api/culture', '/api/historical-tree'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, response.get_data(as_text=True))

    def test_public_products_do_not_expose_owner_or_email(self):
        response = self.client.get('/api/products')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['count'], 1)
        product = response.json['products'][0]
        self.assertEqual(product['name'], 'Produk uji')
        self.assertIs(product['is_owner'], False)
        self.assertEqual(product['seller_name'], 'Penjual UMKM')
        self.assertNotIn('private-seller@example.test', response.get_data(as_text=True))

    def test_seller_still_has_owner_access(self):
        response = self.client.get('/api/products', headers={
            'Authorization': f'Bearer {self.seller_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json['products'][0]['is_owner'], True)
        mine = self.client.get('/api/products/mine', headers={
            'Authorization': f'Bearer {self.seller_token}'})
        self.assertEqual(mine.status_code, 200)

    def test_guest_cannot_access_private_or_edit_routes(self):
        requests = [
            ('get', '/api/auth/me'),
            ('get', '/api/products/mine'),
            ('get', '/api/family'),
            ('get', '/api/profile/me'),
            ('get', '/api/historical-tree/admin'),
            ('post', '/api/products'),
        ]
        for method, route in requests:
            with self.subTest(route=route):
                response = getattr(self.client, method)(route)
                self.assertIn(response.status_code, (401, 403))

    def test_support_url_requires_real_contact(self):
        with patch.dict(os.environ, {'SUPPORT_EMAIL': '', 'SUPPORT_CONTACT_URL': ''}):
            self.assertEqual(self.client.get('/legal/support').status_code, 503)
        with patch.dict(os.environ, {'SUPPORT_EMAIL': 'help@example.com',
                                     'SUPPORT_CONTACT_URL': ''}):
            response = self.client.get('/legal/support')
            self.assertEqual(response.status_code, 200)
            self.assertIn('mailto:help@example.com', response.get_data(as_text=True))
        with patch.dict(os.environ, {'SUPPORT_EMAIL': 'a"<script>@example.com',
                                     'SUPPORT_CONTACT_URL': ''}):
            response = self.client.get('/legal/support')
            self.assertNotIn('<script>', response.get_data(as_text=True))

    def test_account_deletion_erases_identity_but_preserves_node(self):
        user = User(email='delete-this@example.test', password_hash='hash',
                    role=User.ROLE_MEMBER, is_active=True, is_email_verified=True)
        db.session.add(user)
        db.session.flush()
        person = Person(user_id=user.id, full_name='Private Person', gender='female')
        db.session.add(person)
        db.session.commit()
        person_id = person.id
        token = create_access_token(identity=str(user.id))
        response = self.client.delete('/api/account', headers={
            'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        node = db.session.get(Person, person_id)
        self.assertIsNotNone(node)
        self.assertIsNone(node.user_id)
        self.assertEqual(node.full_name, 'Profil dihapus')
        self.assertIsNone(node.gender)
        self.assertIsNone(node.birth_date)
        self.assertIsNone(db.session.get(User, user.id))


if __name__ == '__main__':
    unittest.main()
