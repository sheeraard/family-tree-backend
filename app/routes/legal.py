import os

from flask import (
    Blueprint,
    Response,
)
from markupsafe import escape


legal_bp = Blueprint(
    "legal",
    __name__,
)


PRIVACY_POLICY_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>Kebijakan Privasi - GEKRAFS</title>

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
            max-width: 850px;
            margin: 0 auto;
            padding: 32px 20px 64px;
            line-height: 1.7;
            color: #202124;
        }

        h1, h2 {
            color: #111827;
        }

        h1 {
            margin-bottom: 4px;
        }

        .updated {
            color: #6b7280;
            margin-bottom: 32px;
        }

        section {
            margin-top: 30px;
        }
    </style>
</head>

<body>
    <h1>Kebijakan Privasi GEKRAFS</h1>

    <div class="updated">
        Terakhir diperbarui: 12 September 2026
    </div>

    <p>
        Kebijakan Privasi ini menjelaskan bagaimana aplikasi
        GEKRAFS mengumpulkan, menggunakan, menyimpan, dan
        melindungi informasi pengguna.
    </p>

    <section>
        <h2>1. Informasi yang Kami Kumpulkan</h2>

        <p>
            Saat menggunakan GEKRAFS, pengguna dapat memberikan
            informasi seperti:
        </p>

        <ul>
            <li>Nama lengkap</li>
            <li>Alamat email</li>
            <li>Nomor telepon</li>
            <li>Tanggal lahir</li>
            <li>Jenis kelamin</li>
            <li>Foto profil</li>
            <li>Informasi hubungan keluarga dan silsilah</li>
            <li>Informasi UMKM atau usaha</li>
            <li>Informasi produk yang dipublikasikan pengguna</li>
            <li>Konten yang dikirim melalui fitur komunitas</li>
        </ul>
    </section>

    <section>
        <h2>2. Penggunaan Informasi</h2>

        <p>
            Informasi digunakan untuk menyediakan dan
            mengoperasikan fitur GEKRAFS, termasuk:
        </p>

        <ul>
            <li>Membuat dan mengelola akun</li>
            <li>Memverifikasi alamat email</li>
            <li>Membangun dan menampilkan silsilah keluarga</li>
            <li>Mengelola profil pengguna</li>
            <li>
                Memproses pendaftaran dan verifikasi UMKM
            </li>
            <li>Menampilkan produk dan informasi usaha</li>
            <li>Menyediakan fitur komunitas</li>
            <li>
                Menjaga keamanan dan mencegah penyalahgunaan
                layanan
            </li>
        </ul>
    </section>

    <section>
        <h2>3. Data Silsilah Keluarga</h2>

        <p>
            GEKRAFS memungkinkan pengguna membuat hubungan
            keluarga dan menambahkan anggota keluarga ke dalam
            silsilah.
        </p>

        <p>
            Karena silsilah merupakan data yang saling terhubung,
            sebuah entri orang dapat tetap berada di dalam
            silsilah setelah akun pengguna terkait dihapus.
        </p>

        <p>
            Dalam kondisi tersebut, hubungan antara akun dan
            profil akan dilepas dan informasi akun pribadi yang
            tidak diperlukan akan dihapus.
        </p>
    </section>

    <section>
        <h2>4. Penyimpanan dan Keamanan Data</h2>

        <p>
            Kami menggunakan langkah teknis yang wajar untuk
            melindungi informasi pengguna dari akses,
            perubahan, penggunaan, atau pengungkapan yang
            tidak sah.
        </p>

        <p>
            Meskipun demikian, tidak ada sistem elektronik yang
            dapat menjamin keamanan secara mutlak.
        </p>
    </section>

    <section>
        <h2>5. Pembagian Informasi</h2>

        <p>
            GEKRAFS tidak menjual data pribadi pengguna.
        </p>

        <p>
            Informasi dapat diproses oleh penyedia infrastruktur
            yang digunakan untuk menjalankan layanan, sejauh
            diperlukan untuk pengoperasian aplikasi.
        </p>

        <p>
            Informasi juga dapat diberikan apabila diwajibkan
            berdasarkan hukum yang berlaku.
        </p>
    </section>

    <section>
        <h2>6. Konten Publik</h2>

        <p>
            Informasi yang secara sengaja dipublikasikan melalui
            fitur seperti produk, UMKM, komunitas, atau konten
            lain yang bersifat publik dapat dilihat oleh
            pengguna lain sesuai fungsi aplikasi.
        </p>
    </section>

    <section>
        <h2>7. Penghapusan Akun</h2>

        <p>
            Pengguna dapat meminta penghapusan akun melalui
            fitur Delete Account pada aplikasi.
        </p>

        <p>
            Saat akun dihapus, kredensial login dan data akun
            terkait akan dihapus atau dilepaskan dari profil
            silsilah.
        </p>

        <p>
            Entri seseorang dalam silsilah dapat dipertahankan
            apabila diperlukan untuk menjaga hubungan keluarga
            pengguna lain tetap utuh.
        </p>
    </section>

    <section>
        <h2>8. Perubahan Kebijakan</h2>

        <p>
            Kebijakan Privasi dapat diperbarui untuk
            menyesuaikan perubahan fitur, teknologi, atau
            ketentuan hukum.
        </p>

        <p>
            Tanggal pembaruan terbaru akan dicantumkan pada
            halaman ini.
        </p>
    </section>

    <section>
        <h2>9. Kontak</h2>

        <p>
            Pertanyaan mengenai privasi atau penggunaan data
            dapat disampaikan melalui kanal kontak resmi
            GEKRAFS.
        </p>
    </section>
</body>
</html>
"""


TERMS_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Syarat dan Ketentuan - GEKRAFS</title>

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
            max-width: 850px;
            margin: 0 auto;
            padding: 32px 20px 64px;
            line-height: 1.7;
            color: #202124;
        }

        h1, h2 {
            color: #111827;
        }

        h1 {
            margin-bottom: 4px;
        }

        .updated {
            color: #6b7280;
            margin-bottom: 32px;
        }

        section {
            margin-top: 30px;
        }
    </style>
</head>

<body>
    <h1>Syarat dan Ketentuan GEKRAFS</h1>

    <div class="updated">
        Terakhir diperbarui: 12 September 2026
    </div>

    <p>
        Dengan membuat akun atau menggunakan aplikasi GEKRAFS,
        pengguna menyetujui Syarat dan Ketentuan berikut.
    </p>

    <section>
        <h2>1. Penggunaan Layanan</h2>

        <p>
            Pengguna wajib menggunakan GEKRAFS secara sah dan
            tidak menggunakan aplikasi untuk aktivitas yang
            melanggar hukum, merugikan pihak lain, atau
            mengganggu layanan.
        </p>
    </section>

    <section>
        <h2>2. Akun Pengguna</h2>

        <p>
            Pengguna bertanggung jawab menjaga keamanan
            kredensial akun dan bertanggung jawab atas aktivitas
            yang dilakukan melalui akunnya.
        </p>

        <p>
            Informasi yang diberikan saat pendaftaran harus
            akurat sejauh pengguna mengetahuinya.
        </p>
    </section>

    <section>
        <h2>3. Silsilah Keluarga</h2>

        <p>
            Pengguna dapat membuat, menghubungkan, atau mengklaim
            profil keluarga sesuai fitur yang tersedia.
        </p>

        <p>
            Pengguna tidak boleh dengan sengaja memasukkan
            informasi palsu, menyesatkan, atau menggunakan data
            orang lain dengan tujuan merugikan pihak tersebut.
        </p>
    </section>

    <section>
        <h2>4. Silsilah Sejarah</h2>

        <p>
            Silsilah sejarah merupakan konten yang dikelola oleh
            administrator.
        </p>

        <p>
            Informasi sejarah dapat berasal dari berbagai sumber
            dan tidak dimaksudkan sebagai jaminan mutlak atas
            keakuratan genealogis atau historis.
        </p>
    </section>

    <section>
        <h2>5. UMKM dan Etalase</h2>

        <p>
            Akun yang ingin menggunakan fitur penjual atau UMKM
            dapat diwajibkan melalui proses persetujuan
            administrator.
        </p>

        <p>
            Pengguna bertanggung jawab atas informasi usaha,
            produk, harga, kontak, deskripsi, dan informasi lain
            yang dipublikasikannya.
        </p>

        <p>
            GEKRAFS berhak menghapus atau membatasi konten yang
            melanggar ketentuan layanan.
        </p>
    </section>

    <section>
        <h2>6. Konten Pengguna</h2>

        <p>
            Pengguna tetap bertanggung jawab terhadap konten
            yang mereka kirim melalui aplikasi.
        </p>

        <p>
            Konten tidak boleh berisi materi yang melanggar
            hukum, menipu, mengancam, atau melanggar hak pihak
            lain.
        </p>
    </section>

    <section>
        <h2>7. Moderasi</h2>

        <p>
            Administrator dapat melakukan moderasi terhadap
            konten, aplikasi UMKM, produk, atau akun apabila
            diperlukan untuk menjaga keamanan dan kualitas
            layanan.
        </p>
    </section>

    <section>
        <h2>8. Penghapusan Akun</h2>

        <p>
            Pengguna dapat menghapus akun melalui fitur yang
            tersedia pada aplikasi.
        </p>

        <p>
            Penghapusan akun tidak selalu menghapus entri
            seseorang dari silsilah keluarga apabila entri
            tersebut diperlukan sebagai bagian dari hubungan
            keluarga pengguna lain.
        </p>
    </section>

    <section>
        <h2>9. Ketersediaan Layanan</h2>

        <p>
            Kami berupaya menjaga layanan tetap tersedia,
            tetapi tidak menjamin bahwa layanan akan selalu
            tersedia tanpa gangguan atau kesalahan.
        </p>
    </section>

    <section>
        <h2>10. Perubahan Layanan</h2>

        <p>
            Fitur, kebijakan, atau Syarat dan Ketentuan dapat
            diperbarui dari waktu ke waktu.
        </p>
    </section>

    <section>
        <h2>11. Kontak</h2>

        <p>
            Pertanyaan mengenai penggunaan aplikasi dapat
            disampaikan melalui kanal kontak resmi GEKRAFS.
        </p>
    </section>
</body>
</html>
"""


SUPPORT_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>Dukungan - Caruban Nagari</title>

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
            max-width: 850px;
            margin: 0 auto;
            padding: 32px 20px 64px;
            line-height: 1.7;
            color: #202124;
        }

        h1, h2 {
            color: #111827;
        }

        h1 {
            margin-bottom: 4px;
        }

        .subtitle {
            color: #6b7280;
            margin-bottom: 32px;
        }

        section {
            margin-top: 30px;
        }

        .contact {
            border: 1px solid #d1d5db;
            border-radius: 14px;
            padding: 18px;
            background: #f9fafb;
        }

        a {
            color: #087fa8;
        }
    </style>
</head>

<body>
    <h1>Dukungan Caruban Nagari</h1>

    <div class="subtitle">
        Bantuan penggunaan aplikasi Caruban Nagari.
    </div>

    <section>
        <h2>Akun dan Masuk</h2>

        <p>
            Jika mengalami kendala masuk, verifikasi email,
            atau lupa kata sandi, gunakan fitur yang tersedia
            pada halaman masuk aplikasi.
        </p>
    </section>

    <section>
        <h2>Silsilah Keluarga</h2>

        <p>
            Untuk kendala terkait anggota keluarga, hubungan
            keluarga, kode klaim, atau tampilan silsilah,
            sertakan penjelasan singkat mengenai masalah yang
            terjadi saat menghubungi dukungan.
        </p>
    </section>

    <section>
        <h2>Silsilah Sejarah</h2>

        <p>
            Informasi sejarah disajikan berdasarkan sumber yang
            digunakan oleh pengelola. Apabila menemukan data
            yang perlu dikoreksi atau ditinjau, silakan
            hubungi tim pengelola.
        </p>
    </section>

    <section>
        <h2>UMKM dan Etalase</h2>

        <p>
            Bantuan mengenai pendaftaran UMKM, status
            persetujuan, produk, atau informasi usaha dapat
            disampaikan kepada tim pengelola Caruban Nagari.
        </p>
    </section>

    <section>
        <h2>Kontak Dukungan</h2>

        <div class="contact">
            {{SUPPORT_CONTACT}}
        </div>
    </section>

    <section>
        <h2>Dokumen</h2>

        <p>
            <a href="/legal/privacy">Kebijakan Privasi</a>
            &nbsp;•&nbsp;
            <a href="/legal/terms">Syarat dan Ketentuan</a>
            &nbsp;•&nbsp;
            <a href="/legal/account-deletion">Penghapusan Akun</a>
        </p>
    </section>
</body>
</html>
"""


ACCOUNT_DELETION_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>Penghapusan Akun - Caruban Nagari</title>

    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
            max-width: 850px;
            margin: 0 auto;
            padding: 32px 20px 64px;
            line-height: 1.7;
            color: #202124;
        }

        h1, h2 {
            color: #111827;
        }

        h1 {
            margin-bottom: 4px;
        }

        .subtitle {
            color: #6b7280;
            margin-bottom: 32px;
        }

        section {
            margin-top: 30px;
        }

        .contact {
            border: 1px solid #d1d5db;
            border-radius: 14px;
            padding: 18px;
            background: #f9fafb;
        }

        .notice {
            border-left: 4px solid #087fa8;
            padding: 12px 16px;
            background: #f0f9ff;
        }

        a {
            color: #087fa8;
        }
    </style>
</head>

<body>
    <h1>Penghapusan Akun Caruban Nagari</h1>

    <div class="subtitle">
        Permintaan penghapusan akun dan data terkait.
    </div>

    <p>
        Pengguna Caruban Nagari dapat meminta penghapusan akun
        beserta data yang terkait dengan akun tersebut.
    </p>

    <section>
        <h2>Hapus langsung dari aplikasi</h2>

        <p>
            Jika Anda masih dapat masuk ke aplikasi, buka
            <strong>Profile</strong> lalu pilih
            <strong>Delete Account</strong>. Setelah dikonfirmasi,
            akun akan dihapus dan Anda akan keluar dari aplikasi.
        </p>
    </section>

    <section>
        <h2>Ajukan permintaan tanpa aplikasi</h2>

        <p>
            Jika Anda sudah menghapus aplikasi atau tidak dapat
            mengakses akun, Anda tetap dapat meminta penghapusan
            melalui email dukungan di bawah ini.
        </p>

        <div class="contact">
            {{DELETION_CONTACT}}
        </div>

        <p>
            Kirim permintaan dari alamat email yang terdaftar pada
            akun Caruban Nagari, atau cantumkan alamat email akun
            yang ingin dihapus agar kepemilikan akun dapat
            diverifikasi.
        </p>

        <p>
            Jangan pernah mengirimkan kata sandi melalui email.
        </p>
    </section>

    <section>
        <h2>Data yang dihapus</h2>

        <p>
            Setelah permintaan penghapusan berhasil diproses,
            kredensial login dan data pribadi yang terkait langsung
            dengan akun akan dihapus atau dilepaskan dari profil
            keluarga. Data lain yang bergantung pada akun, seperti
            data usaha atau produk yang terkait dengan akun, juga
            dapat dihapus sesuai struktur layanan.
        </p>
    </section>

    <section>
        <h2>Data silsilah yang dapat dipertahankan</h2>

        <div class="notice">
            Entri orang dalam silsilah keluarga dapat tetap
            dipertahankan tanpa hubungan ke akun pengguna apabila
            diperlukan untuk menjaga hubungan keluarga pengguna
            lain tetap utuh. Informasi akun pribadi yang tidak
            diperlukan akan dihapus atau dilepaskan dari entri
            tersebut.
        </div>
    </section>

    <section>
        <h2>Dokumen terkait</h2>

        <p>
            <a href="/legal/privacy">Kebijakan Privasi</a>
            &nbsp;•&nbsp;
            <a href="/legal/terms">Syarat dan Ketentuan</a>
            &nbsp;•&nbsp;
            <a href="/legal/support">Dukungan</a>
        </p>
    </section>
</body>
</html>
"""


@legal_bp.route(
    "/privacy",
    methods=["GET"],
)
def privacy_policy():
    return Response(
        PRIVACY_POLICY_HTML,
        status=200,
        mimetype="text/html",
    )


@legal_bp.route(
    "/terms",
    methods=["GET"],
)
def terms():
    return Response(
        TERMS_HTML,
        status=200,
        mimetype="text/html",
    )


@legal_bp.route(
    "/support",
    methods=["GET"],
)
def support():
    support_email = os.getenv(
        "SUPPORT_EMAIL",
        "",
    ).strip()

    if support_email:
        safe_email = escape(
            support_email
        )

        contact_html = (
            "<p>"
            "Email: "
            f'<a href="mailto:{safe_email}">'
            f"{safe_email}"
            "</a>"
            "</p>"
            "<p>"
            "Sertakan jenis perangkat, versi aplikasi, "
            "dan penjelasan singkat mengenai kendala."
            "</p>"
        )
    else:
        contact_html = (
            "<p>"
            "Silakan hubungi kanal kontak resmi "
            "Caruban Nagari / GEKRAFS Cirebon."
            "</p>"
        )

    html = SUPPORT_HTML.replace(
        "{{SUPPORT_CONTACT}}",
        str(contact_html),
    )

    return Response(
        html,
        status=200,
        mimetype="text/html",
    )


@legal_bp.route(
    "/account-deletion",
    methods=["GET"],
)
def account_deletion():
    support_email = os.getenv(
        "SUPPORT_EMAIL",
        "",
    ).strip()

    if support_email:
        safe_email = escape(
            support_email
        )

        contact_html = (
            "<p>"
            "Email: "
            f'<a href="mailto:{safe_email}'
            "?subject=Permintaan%20Penghapusan%20Akun%20"
            'Caruban%20Nagari">'
            f"{safe_email}"
            "</a>"
            "</p>"
            "<p>"
            "Subjek yang disarankan: "
            "<strong>Permintaan Penghapusan Akun "
            "Caruban Nagari</strong>"
            "</p>"
        )
    else:
        contact_html = (
            "<p>"
            "gekrafs.noreply@gmail.com"
            "</p>"
        )

    html = ACCOUNT_DELETION_HTML.replace(
        "{{DELETION_CONTACT}}",
        str(contact_html),
    )

    return Response(
        html,
        status=200,
        mimetype="text/html",
    )

