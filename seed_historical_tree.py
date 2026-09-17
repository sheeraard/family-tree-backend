"""Seed Caruban Nagari historical genealogy as linked small-family groups.

Run from the backend project root:
    python seed_historical_tree.py

Model:
- Historical people and parent/child relationships remain global.
- Every person that has direct children in the source becomes the head of one
  small family group.
- A child that later has children of their own naturally becomes the head of
  another group, so the UI can continue from one family to the next.
- The source contains 246 people, 244 parent/child relationships, and 18
  small-family groups.

The seed is idempotent for records created by this script:
- deterministic UUIDv5 IDs are used;
- re-running updates seeded rows instead of duplicating them;
- unrelated/manual people and relationships are untouched;
- the two legacy Step 20.2 whole-tree groups created by an earlier seed are
  removed by deterministic ID because they are no longer part of the model.
"""

from __future__ import annotations

import uuid

from app import create_app
from app.extensions import db
from app.models.historical_tree_group import HistoricalTreeGroup
from app.models.historical_person import HistoricalPerson
from app.models.historical_relationship import HistoricalRelationship

SOURCE = "SALINAN SILSILAH 2021 NASKAH RANTE KERATON KANOMAN.docx"
NAMESPACE = uuid.UUID("3cc95cc4-24e4-4f8a-8f40-c3fb7a2d39af")


def stable_uuid(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"{kind}:{key}")


PEOPLE = [{'key': 'sgj',
  'name': 'Maulana Syarif Hidayatullah / Sunan Gunung Jati',
  'description': 'Memerintah (1479–1528).'},
 {'key': 'sgj_bratakelana', 'name': 'Pangeran Bratakelana', 'description': None},
 {'key': 'sgj_jayakelana', 'name': 'Pangeran Jayakelana', 'description': None},
 {'key': 'sgj_trusmi', 'name': 'Pangeran Trusmi', 'description': None},
 {'key': 'sgj_sabakingking', 'name': 'Pangeran Sabakingking', 'description': None},
 {'key': 'sgj_ratu_mas_ayu', 'name': 'Ratu Mas Ayu', 'description': 'Garwa Pangeran Tuban.'},
 {'key': 'sgj_ratu_wulung_ayu',
  'name': 'Ratu Wulung Ayu',
  'description': 'Garwa Pangeran Paseh / Fathillah, putra Raja Aceh.'},
 {'key': 'sgj_pesaraean', 'name': 'Pangeran Pesaraean', 'description': 'Memerintah (1529–1552).'},
 {'key': 'sgj_ratu_martasari', 'name': 'Ratu Martasari', 'description': 'Garwa Pangeran Palakaran.'},
 {'key': 'wulung_ratu_agung', 'name': 'Ratu Agung', 'description': None},
 {'key': 'wulung_pangeran_paseh', 'name': 'Pangeran Paseh', 'description': None},
 {'key': 'wulung_pangeran_pekik', 'name': 'Pangeran Pekik', 'description': None},
 {'key': 'wulung_pangeran_agung', 'name': 'Pangeran Agung', 'description': None},
 {'key': 'wulung_ratu_wanawati', 'name': 'Ratu Wanawati', 'description': 'Garwa Pangeran Dipati Cerbon.'},
 {'key': 'pesaraean_kesatriyan', 'name': 'Pangeran Kesatriyan', 'description': None},
 {'key': 'pesaraean_ratu_winaon', 'name': 'Ratu Winaon', 'description': None},
 {'key': 'pesaraean_ratu_emas',
  'name': 'Ratu Emas',
  'description': 'Garwa Tu Bagus Angke, putra Sultan Banten.'},
 {'key': 'pesaraean_dipati_anom_carbon', 'name': 'Pangeran Dipati Anom Carbon', 'description': None},
 {'key': 'pesaraean_panembahan_losari', 'name': 'Panembahan Losari', 'description': None},
 {'key': 'pesaraean_pangeran_waruju', 'name': 'Pangeran Waruju', 'description': None},
 {'key': 'martasari_pangeran_santri', 'name': 'Pangeran Santri', 'description': 'Garwa Pucuk Umun.'},
 {'key': 'santri_prabu_geusan_ulun', 'name': 'Prabu Geusan Ulun / Angkawijaya', 'description': None},
 {'key': 'sedang_kemuning',
  'name': 'Pangeran Sedang Kemuning / Dipati Carbon I',
  'description': 'The source begins this branch separately and does not explicitly state this person’s '
                 'parent in the supplied text.'},
 {'key': 'panembahan_ratu_cerbon_kasiji', 'name': 'Panembahan Ratu Cerbon Kasiji', 'description': None},
 {'key': 'sedang_kemuning_pangeran_manis', 'name': 'Pangeran Manis', 'description': None},
 {'key': 'sedang_kemuning_pangeran_wirasuta', 'name': 'Pangeran Wirasuta', 'description': None},
 {'key': 'sedang_kemuning_ratu_sewuh', 'name': 'Ratu Sewuh', 'description': None},
 {'key': 'kasiji_wiranagara', 'name': 'Pangeran Wiranagara', 'description': None},
 {'key': 'kasiji_ratu_ranamanggala', 'name': 'Ratu Ranamanggala', 'description': None},
 {'key': 'kasiji_ratu_singawangun', 'name': 'Ratu Singawangun', 'description': None},
 {'key': 'kasiji_tanu_adiarsa', 'name': 'Pangeran Tanu Adiarsa', 'description': None},
 {'key': 'kasiji_sedang_belimbing', 'name': 'Pangeran Sedang Belimbing', 'description': None},
 {'key': 'kasiji_arya_kidul', 'name': 'Pangeran Arya Kidul', 'description': None},
 {'key': 'kasiji_adipati_sedang_gayam',
  'name': 'Pangeran Adipati Cerbon / Pangeran Adipati Sedang Gayam',
  'description': "Earlier in the source this appears as 'Pangeran Adipati kopi Carbon atawa Pangeran Adipati "
                 "Sedang Gayam'. The later heading uses 'Pangeran Adipati Cerbon atawa Pangeran Adipati "
                 "Sedanggayam'."},
 {'key': 'sedang_gayam_ratu_puteri', 'name': 'Ratu Puteri', 'description': None},
 {'key': 'girilaya', 'name': 'Panembahan Ratu Cerbon Kapingdo Girilaya', 'description': None},
 {'key': 'girilaya_suryaningrat', 'name': 'Pangeran Suryaningrat', 'description': None},
 {'key': 'girilaya_suryamanggala', 'name': 'Pangeran Suryamanggala', 'description': None},
 {'key': 'girilaya_surajaya', 'name': 'Pangeran Surajaya', 'description': None},
 {'key': 'girilaya_nataningrat_tanjung_kaling',
  'name': 'Pangeran Arya Nataningrat Tanjung Kaling',
  'description': None},
 {'key': 'girilaya_ratu_galampo', 'name': 'Ratu Galampo', 'description': None},
 {'key': 'girilaya_ratu_katijah', 'name': 'Ratu Katijah', 'description': None},
 {'key': 'girilaya_pangeran_alas', 'name': 'Pangeran Alas', 'description': None},
 {'key': 'girilaya_kusumajaya_kajawanan', 'name': 'Pangeran Kusumajaya Kajawanan', 'description': None},
 {'key': 'girilaya_suryadiradiya', 'name': 'Pangeran Suryadiradiya', 'description': None},
 {'key': 'girilaya_wangsakerta', 'name': 'Panembahan Katimang Wangsakerta Kasiji', 'description': None},
 {'key': 'badridin_1',
  'name': 'Sultan Anom Gusti Badridin Kartawijaya Kanoman Kaping Siji (1)',
  'description': None},
 {'key': 'girilaya_kartaningrat', 'name': 'Pangeran Kartaningrat', 'description': None},
 {'key': 'girilaya_samsudin_martawijaya',
  'name': 'Sultan Sepuh Samsudin Martawijaya Kasiji',
  'description': None},
 {'key': 'badridin_01_putera', 'name': 'Pangeran Putera', 'description': None},
 {'key': 'badridin_02_mas_rara', 'name': 'Ratu Mas Rara', 'description': None},
 {'key': 'badridin_03_kirana', 'name': 'Ratu Kirana', 'description': None},
 {'key': 'badridin_04_arya_lor', 'name': 'Ratu Arya Lor', 'description': None},
 {'key': 'badridin_05_arya_kencana', 'name': 'Ratu Arya Kencana', 'description': None},
 {'key': 'badridin_06_arya_kulon', 'name': 'Ratu Arya Kulon', 'description': None},
 {'key': 'badridin_07_agung', 'name': 'Ratu Agung', 'description': None},
 {'key': 'badridin_08_godong', 'name': 'Ratu Godong', 'description': None},
 {'key': 'badridin_09_mas_tahjiyah', 'name': 'Ratu Mas Tahjiyah', 'description': None},
 {'key': 'badridin_10_arya_kidul', 'name': 'Ratu Arya Kidul', 'description': None},
 {'key': 'badridin_11_dipati_kedaton', 'name': 'Pangeran Dipati Kedaton', 'description': None},
 {'key': 'badridin_12_kelungsu', 'name': 'Ratu Kelungsu', 'description': None},
 {'key': 'badridin_13_adipati_atanggah', 'name': 'Pangeran Adipati Atanggah', 'description': None},
 {'key': 'badridin_14_ampaitan', 'name': 'Ratu Ampaitan', 'description': None},
 {'key': 'badridin_15_adipati_ranamanggala', 'name': 'Pangeran Adipati Ranamanggala', 'description': None},
 {'key': 'badridin_16_adipati_raja_kusuma', 'name': 'Pangeran Adipati Raja Kusuma', 'description': None},
 {'key': 'badridin_17_kaprabon_sulaiman',
  'name': 'Pangeran Adipati Kaprabon Sulaiman Kaprabonan',
  'description': None},
 {'key': 'badridin_18_anggur', 'name': 'Ratu Anggur', 'description': None},
 {'key': 'badridin_19_partawijaya', 'name': 'Pangeran Partawijaya', 'description': None},
 {'key': 'badridin_20_bagus', 'name': 'Pangeran Bagus', 'description': None},
 {'key': 'badridin_21_kawisnata', 'name': 'Pangeran Kawisnata', 'description': None},
 {'key': 'badridin_22_ahmad', 'name': 'Pangeran Ahmad', 'description': None},
 {'key': 'badridin_23_ratu', 'name': 'Pangeran Ratu', 'description': None},
 {'key': 'badridin_24_pekik', 'name': 'Pangeran Pekik', 'description': None},
 {'key': 'badridin_25_duwah', 'name': 'Pangeran Duwah', 'description': None},
 {'key': 'badridin_26_arya_panengag', 'name': 'Pangeran Arya Panengag', 'description': None},
 {'key': 'badridin_27_adipati_madengda', 'name': 'Pangeran Adipati Madengda', 'description': None},
 {'key': 'badridin_28_kusuma_ningyun', 'name': 'Pangeran Kusuma Ningyun', 'description': None},
 {'key': 'badridin_29_rana', 'name': 'Pangeran Rana', 'description': None},
 {'key': 'badridin_30_adipati_pringgabaya', 'name': 'Pangeran Adipati Pringgabaya', 'description': None},
 {'key': 'badridin_31_duwet', 'name': 'Pangeran Duwet', 'description': None},
 {'key': 'badridin_32_raja_kiyandra', 'name': 'Ratu Raja Kiyandra', 'description': None},
 {'key': 'badridin_33_adipati_raja_putra', 'name': 'Pangeran Adipati Raja Putra', 'description': None},
 {'key': 'kalirudin_2',
  'name': 'Sultan Anom Kalirudin Kanoman Kaping Pindo (2) / Sultan Mandurareja',
  'description': None},
 {'key': 'kalirudin_01_nataningrat', 'name': 'Ratu Nataningrat', 'description': None},
 {'key': 'kalirudin_02_surawijaya', 'name': 'Ratu Surawijaya', 'description': None},
 {'key': 'kalirudin_03_dipati', 'name': 'Ratu Dipati', 'description': None},
 {'key': 'kalirudin_04_bonggol', 'name': 'Ratu Bonggol', 'description': None},
 {'key': 'kalirudin_05_martasari', 'name': 'Ratu Martasari', 'description': None},
 {'key': 'kalirudin_06_ngumar', 'name': 'Pangeran Ngumar', 'description': None},
 {'key': 'kalirudin_07_abdul_wali', 'name': 'Pangeran Gusti Abdul Wali', 'description': None},
 {'key': 'kalirudin_08_wisu', 'name': 'Pangeran Wisu', 'description': None},
 {'key': 'kalirudin_09_karna', 'name': 'Pangeran Karna', 'description': None},
 {'key': 'alimudin_3',
  'name': 'Sultan Kanoman Alimudin / Ngalimudin Kanoman Kaping Telu (3)',
  'description': "The child list spells the name 'Sultan Ngalimudin Kanoman Kaping Telu'; the following "
                 "heading spells it 'Sultan Kanoman Alimudin Kanoman Kaping Telu (3)'."},
 {'key': 'alimudin_01_warok', 'name': 'Pangeran Warok', 'description': None},
 {'key': 'alimudin_02_raja_anom_tangad', 'name': 'Pangeran Raja Anom Tangad', 'description': None},
 {'key': 'alimudin_03_jeruk', 'name': 'Pangeran Jeruk', 'description': None},
 {'key': 'hairidin_4',
  'name': 'Sultan Anom Hairidin / Khaerudin Kanoman Kaping Papat (4)',
  'description': "The child list uses 'Hairidin'; the following heading uses 'Hairidin/Khaerudin'."},
 {'key': 'hairidin_01_nuruddin', 'name': 'Pangeran Raja Kabupaten Nuruddin', 'description': None},
 {'key': 'hairidin_02_ngarab_ngorat', 'name': 'Pangeran Raja Ngarab / Ngorat', 'description': None},
 {'key': 'hairidin_03_cerbon_suni',
  'name': 'Ratu Raja Cerbon Suni',
  'description': "The source marks this entry 'tdk terbaca' (not clearly readable)."},
 {'key': 'hairidin_04_mandurareja_ngabid', 'name': 'Pangeran Raja Mandurareja Ngabid', 'description': None},
 {'key': 'hairidin_05_jafarudin', 'name': 'Pangeran Jafarudin', 'description': None},
 {'key': 'hairidin_06_muhayidin', 'name': 'Pangeran Muhayidin', 'description': None},
 {'key': 'hairidin_07_kayudin_ngasikin', 'name': 'Pangeran Muhammad Kayudin Ngasikin', 'description': None},
 {'key': 'hairidin_08_ngaripin_ngasidin', 'name': 'Pangeran Raja Ngaripin Ngasidin', 'description': None},
 {'key': 'hairidin_09_muhammad_mangkur', 'name': 'Pangeran Raja Muhammad Mangkur', 'description': None},
 {'key': 'hairidin_10_rogawa_suaima', 'name': 'Pangeran Raja Rogawa Suaima', 'description': None},
 {'key': 'hairidin_11_kesatriya_timbul', 'name': 'Pangeran Raja Kesatriya Timbul', 'description': None},
 {'key': 'hairidin_12_mundira', 'name': 'Ratu Mundira', 'description': None},
 {'key': 'hairidin_13_kanigara', 'name': 'Pangeran Kanigara', 'description': None},
 {'key': 'hairidin_14_mangkaradiya', 'name': 'Ratu Raja Mangkaradiya', 'description': None},
 {'key': 'hairidin_15_carhizah', 'name': 'Ratu Carhizah', 'description': None},
 {'key': 'hairidin_16_kusuma_hasanudin', 'name': 'Pangeran Raja Kusuma Hasanudin', 'description': None},
 {'key': 'hairidin_17_iskandar', 'name': 'Pangeran Raja Iskandar', 'description': None},
 {'key': 'hairidin_18_putera_mahmud', 'name': 'Pangeran Raja Putera Mahmud', 'description': None},
 {'key': 'hairidin_19_bawangin_abu_saat', 'name': 'Pangeran Raja Bawangin Abu Saat', 'description': None},
 {'key': 'hairidin_20_murti_katifah', 'name': 'Ratu Raja Murti Katifah', 'description': None},
 {'key': 'hairidin_21_ngaripin_sahidin', 'name': 'Pangeran Ngaripin Sahidin', 'description': None},
 {'key': 'hairidin_22_lakon', 'name': 'Ratu Lakon', 'description': None},
 {'key': 'hairidin_23_jaenidin_farilan', 'name': 'Pangeran Raja Jaenidin Farilan', 'description': None},
 {'key': 'hairidin_24_muidah', 'name': 'Ratu Muidah', 'description': None},
 {'key': 'hairidin_25_ailaludin_sangkan', 'name': 'Pangeran Ailaludin Sangkan', 'description': None},
 {'key': 'hairidin_26_mas_rara_talun', 'name': 'Ratu Mas Rara Talun', 'description': None},
 {'key': 'hairidin_27_siwi_ngaidah_guntang_a', 'name': 'Ratu Raja Siwi Ngaidah Guntang', 'description': None},
 {'key': 'hairidin_28_ambetkasih_safiyah', 'name': 'Ratu Raja Ambetkasih Safiyah', 'description': None},
 {'key': 'hairidin_29_gubug', 'name': 'Ratu Gubug', 'description': None},
 {'key': 'hairidin_30_mangkarawati_ngafiyah', 'name': 'Ratu Raja Mangkarawati Ngafiyah', 'description': None},
 {'key': 'hairidin_31_kaputren', 'name': 'Ratu Raja Kaputren', 'description': None},
 {'key': 'hairidin_32_taif', 'name': 'Pangeran Taif', 'description': None},
 {'key': 'hairidin_33_jubaidah', 'name': 'Ratu Jubaidah', 'description': None},
 {'key': 'hairidin_34_datengpura', 'name': 'Pangeran Raja Datengpura', 'description': None},
 {'key': 'hairidin_35_kanoman_arilah', 'name': 'Ratu Raja Kanoman Arilah', 'description': None},
 {'key': 'hairidin_36_somila', 'name': 'Ratu Raja Somila', 'description': None},
 {'key': 'hairidin_37_pakungdiyah', 'name': 'Ratu Raja Pakungdiyah', 'description': None},
 {'key': 'hairidin_38_panengen', 'name': 'Pangeran Raja Panengen', 'description': None},
 {'key': 'hairidin_39_pangiwe', 'name': 'Pangeran Raja Pangiwe', 'description': None},
 {'key': 'hairidin_40_hairidin_kacerbonan',
  'name': 'Pangeran Raja Kanoman / Sultan Hairidin Kacerbonan Sapengadegan',
  'description': None},
 {'key': 'hairidin_41_atas_angin', 'name': 'Pangeran Atas Angin', 'description': None},
 {'key': 'hairidin_42_juwita_al_dul', 'name': 'Ratu Raja Juwita Al Dul', 'description': None},
 {'key': 'hairidin_43_murti_maryam', 'name': 'Ratu Raja Murti Maryam', 'description': None},
 {'key': 'hairidin_44_salu', 'name': 'Ratu Raja Salu', 'description': None},
 {'key': 'hairidin_45_fantara_ngasima', 'name': 'Ratu Raja Fantara Ngasima', 'description': None},
 {'key': 'hairidin_46_gerage_sangida', 'name': 'Ratu Raja Gerage Sangida', 'description': None},
 {'key': 'hairidin_47_jukal', 'name': 'Pangeran Jukal', 'description': None},
 {'key': 'hairidin_48_siwi', 'name': 'Ratu Raja Siwi', 'description': None},
 {'key': 'hairidin_49_siwi_ngaidah_guntang_b',
  'name': 'Ratu Raja Siwi Ngaidah Guntang',
  'description': 'This same name also appears as item 27 in the source; both numbered entries are preserved '
                 'as separate nodes.'},
 {'key': 'hairidin_50_saliyu', 'name': 'Ratu Raja Saliyu', 'description': None},
 {'key': 'hairidin_51_basiroh', 'name': 'Ratu Raja Basiroh', 'description': None},
 {'key': 'hairidin_52_anom_kamil', 'name': 'Pangeran Raja Anom Kamil', 'description': None},
 {'key': 'hairidin_53_tisaya_baijah', 'name': 'Ratu Raja Tisaya Baijah', 'description': None},
 {'key': 'hairidin_54_keraton_rujakah', 'name': 'Ratu Raja Keraton Rujakah', 'description': None},
 {'key': 'hairidin_55_subita_walung_ngantun',
  'name': 'Pangeran Raja Subita Walung Ngantun',
  'description': None},
 {'key': 'hairidin_56_manguntur', 'name': 'Pangeran Raja Manguntur', 'description': None},
 {'key': 'hairidin_57_mandura_abudin', 'name': 'Pangeran Raja Mandura Abudin', 'description': None},
 {'key': 'hairidin_58_padmabrata', 'name': 'Pangeran Padmabrata', 'description': None},
 {'key': 'hairidin_59_warsita', 'name': 'Ratu Warsita', 'description': None},
 {'key': 'hairidin_60_riya_kusumanagara', 'name': 'Pangeran Riya Kusumanagara', 'description': None},
 {'key': 'imamudin_5',
  'name': 'Sultan Anom Imamudin Abu Soleh, Sultan Kanoman Kaping Lima (5)',
  'description': None},
 {'key': 'imamudin_01_siwulan', 'name': 'Ratu Raja Siwulan', 'description': None},
 {'key': 'imamudin_02_kecubung', 'name': 'Ratu Raja Kecubung', 'description': None},
 {'key': 'imamudin_03_bonteng', 'name': 'Ratu Raja Bonteng', 'description': None},
 {'key': 'imamudin_04_winaon', 'name': 'Ratu Raja Winaon', 'description': None},
 {'key': 'imamudin_05_aimi', 'name': 'Ratu Raja Aimi', 'description': None},
 {'key': 'imamudin_06_jaelani', 'name': 'Ratu Raja Jaelani', 'description': None},
 {'key': 'imamudin_07_kulon', 'name': 'Ratu Raja Kulon', 'description': None},
 {'key': 'imamudin_08_walu', 'name': 'Pangeran Raja Walu', 'description': None},
 {'key': 'imamudin_09_brata_pradikta', 'name': "Pangeran Raja Brata Pra' dikta", 'description': None},
 {'key': 'imamudin_10_susilabrata', 'name': 'Ratu Raja Susilabrata', 'description': None},
 {'key': 'imamudin_11_teratai', 'name': 'Ratu Raja Teratai', 'description': None},
 {'key': 'imamudin_12_partawijaya', 'name': 'Pangeran Raja Partawijaya', 'description': None},
 {'key': 'imamudin_13_susila', 'name': 'Pangeran Raja Susila', 'description': None},
 {'key': 'imamudin_14_tangkulak', 'name': 'Pangeran Raja Tangkulak', 'description': None},
 {'key': 'imamudin_15_sudirga', 'name': 'Pangeran Raja Sudirga', 'description': None},
 {'key': 'imamudin_16_bogiyah', 'name': 'Pangeran Raja Bogiyah', 'description': None},
 {'key': 'imamudin_17_kaprabon', 'name': 'Pangeran Raja Kaprabon', 'description': None},
 {'key': 'imamudin_18_nakoda', 'name': 'Pangeran Raja Nakoda', 'description': None},
 {'key': 'kamarudin_6',
  'name': 'Sultan Anom Kamarudin Kanoman Kaping Nenem (6)',
  'description': "The child list omits 'Anom'; the following heading includes it."},
 {'key': 'kamarudin_01_kaprabon', 'name': 'Pangeran Raja Kaprabon', 'description': None},
 {'key': 'kamarudin_02_rogawa', 'name': 'Pangeran Raja Rogawa', 'description': None},
 {'key': 'kamarudin_03_subitaningrat', 'name': 'Pangeran Raja Subitaningrat', 'description': None},
 {'key': 'kamarudin_04_dipati', 'name': 'Ratu Raja Dipati', 'description': None},
 {'key': 'kamarudin_05_dewi', 'name': 'Ratu Raja Dewi', 'description': None},
 {'key': 'kamarudin_06_kartaningrat', 'name': 'Pangeran Raja Kartaningrat', 'description': None},
 {'key': 'kamarudin_07_kartawijaya', 'name': 'Pangeran Raja Kartawijaya', 'description': None},
 {'key': 'kamarudin_08_muhammad_cerbon', 'name': 'Pangeran Raja Muhammad Cerbon', 'description': None},
 {'key': 'nurbuwat_7',
  'name': 'Sultan Anom Kamarudin Raja Nurbuwat, Sultan Kanoman Kaping Pitu (7)',
  'description': None},
 {'key': 'nurbuwat7_01_sularaja', 'name': 'Pangeran Sularaja', 'description': None},
 {'key': 'nurbuwat7_02_brataningrat', 'name': 'Pangeran Brataningrat', 'description': None},
 {'key': 'nurbuwat7_03_saputra_kalirudin', 'name': 'Pangeran Saputra Kalirudin', 'description': None},
 {'key': 'nurbuwat7_04_makbul_kartawijaya', 'name': 'Pangeran Makbul Kartawijaya', 'description': None},
 {'key': 'nurbuwat7_05_garambol_ngaisyah', 'name': 'Ratu Garambol Siti Ngaisyah', 'description': None},
 {'key': 'nurbuwat7_06_waluh_brata_kusuma', 'name': 'Pangeran Waluh Brata Kusuma', 'description': None},
 {'key': 'nurbuwat7_07_pulai_giri', 'name': 'Pangeran Pulai Giri Surya Nurbuwat', 'description': None},
 {'key': 'nurbuwat7_08_saliyah', 'name': 'Ratu Saliyah', 'description': None},
 {'key': 'nurbuwat7_09_arsad_wijayakarta', 'name': 'Pangeran Arsad Wijayakarta', 'description': None},
 {'key': 'nurbuwat7_10_sari_dana', 'name': 'Ratu Sari Dana', 'description': None},
 {'key': 'nurbuwat7_11_rangganingrat', 'name': 'Ratu Rangganingrat', 'description': None},
 {'key': 'nurbuwat7_12_anifah', 'name': 'Pangeran Anifah', 'description': None},
 {'key': 'nurbuwat7_13_raja_diningrat', 'name': 'Ratu Raja Diningrat', 'description': None},
 {'key': 'nurbuwat7_14_kencana_wungu', 'name': 'Ratu Kencana Wungu', 'description': None},
 {'key': 'nurbuwat7_15_sulur_bratamadenga', 'name': 'Pangeran Sulur Bratamadenga', 'description': None},
 {'key': 'nurbuwat7_16_raja_kusumaningrat', 'name': 'Ratu Raja Kusumaningrat', 'description': None},
 {'key': 'nurbuwat7_17_muhammad_dawud', 'name': 'Pangeran Muhammad Dawud', 'description': None},
 {'key': 'nurbuwat7_18_siti_rasmi', 'name': 'Ratu Siti Rasmi', 'description': None},
 {'key': 'nurbuwat7_19_raja_atas_angin', 'name': 'Ratu Raja Atas Angin', 'description': None},
 {'key': 'nurbuwat7_20_raja_cerbon_pangeran', 'name': 'Pangeran Raja Cerbon', 'description': None},
 {'key': 'nurbuwat7_21_raja_cerbon_ratu', 'name': 'Ratu Raja Cerbon', 'description': None},
 {'key': 'nurbuwat7_22_ratna_adiintan', 'name': 'Ratu Ratna Adiintan', 'description': None},
 {'key': 'nurbuwat7_23_silir_hudayabrata', 'name': 'Pangeran Silir Hudayabrata', 'description': None},
 {'key': 'nurbuwat7_24_mandapa', 'name': 'Ratu Mandapa', 'description': None},
 {'key': 'nurbuwat7_25_dzulhaji_prabakusuma', 'name': 'Pangeran Dzulhaji Prabakusuma', 'description': None},
 {'key': 'nurbuwat7_26_siti_fatimah', 'name': 'Ratu Siti Fatimah Kusumaningrat', 'description': None},
 {'key': 'nurbuwat7_27_drajat', 'name': 'Pangeran Drajat', 'description': None},
 {'key': 'nurbuwat7_28_raja_iskandar', 'name': 'Pangeran Raja Iskandar', 'description': None},
 {'key': 'dzulkarnaen_8',
  'name': 'Pangeran Raja Dzulkarnaen, Sultan Kanoman Kaping Wolu (8)',
  'description': "The child list spells 'Kanomna'; the following heading spells 'Kanoman'."},
 {'key': 'dzulkarnaen_01_samsi', 'name': 'Elang Samsi', 'description': None},
 {'key': 'dzulkarnaen_02_nawang', 'name': 'Ratu Nawang', 'description': None},
 {'key': 'dzulkarnaen_03_naam', 'name': 'Elang Naam', 'description': None},
 {'key': 'dzulkarnaen_04_rohani', 'name': 'Elang Rohani', 'description': None},
 {'key': 'dzulkarnaen_05_sari_wulan', 'name': 'Ratu Siti Sari Wulan', 'description': None},
 {'key': 'dzulkarnaen_06_kamam', 'name': 'Ratu Kamam', 'description': None},
 {'key': 'dzulkarnaen_07_siti_padma', 'name': 'Ratu Siti Padma', 'description': None},
 {'key': 'dzulkarnaen_08_suka', 'name': 'Ratu Suka', 'description': None},
 {'key': 'dzulkarnaen_09_siti_hadija', 'name': 'Ratu Siti Hadija', 'description': None},
 {'key': 'dzulkarnaen_10_kusniyah', 'name': 'Ratu Kusniyah', 'description': None},
 {'key': 'dzulkarnaen_11_romla', 'name': 'Ratu Romla', 'description': None},
 {'key': 'dzulkarnaen_13_gumiwang',
  'name': 'Ratu Gumiwang',
  'description': 'The source numbering jumps from 11 to 13; no item 12 is present in the supplied document.'},
 {'key': 'dzulkarnaen_14_siyam', 'name': 'Ratu Siyam', 'description': None},
 {'key': 'dzulkarnaen_15_cahya', 'name': 'Ratu Cahya', 'description': None},
 {'key': 'dzulkarnaen_16_nurani', 'name': 'Ratu Nurani', 'description': None},
 {'key': 'dzulkarnaen_17_jaelani_aryadiradeya', 'name': 'Elang Jaelani Aryadiradeya', 'description': None},
 {'key': 'nurbuwat_9',
  'name': 'Pangeran Raja Nurbuwat, Sultan Kanoman Kaping Sanga (9)',
  'description': None},
 {'key': 'nurbuwat9_01_yusuf', 'name': 'Elang Yusuf', 'description': None},
 {'key': 'nurbuwat9_02_husain', 'name': 'Elang Husain', 'description': None},
 {'key': 'nurbuwat9_03_nurahman', 'name': 'Elang Nurahman', 'description': None},
 {'key': 'nurbuwat9_04_nurana', 'name': 'Elang Nurana', 'description': None},
 {'key': 'nurbuwat9_05_ismail', 'name': 'Elang Ismail', 'description': None},
 {'key': 'nurbuwat9_06_nurun', 'name': 'Elang Nurun', 'description': None},
 {'key': 'nurbuwat9_07_yamin', 'name': 'Elang Yamin', 'description': None},
 {'key': 'nurbuwat9_08_rohmani', 'name': 'Ratu Rohmani', 'description': None},
 {'key': 'nurbuwat9_09_langen', 'name': 'Ratu Langen', 'description': None},
 {'key': 'nurbuwat9_10_nuran', 'name': 'Ratu Nuran', 'description': None},
 {'key': 'nurbuwat9_11_jaenab', 'name': 'Ratu Jaenab', 'description': None},
 {'key': 'nurbuwat9_12_puteri', 'name': 'Ratu Puteri', 'description': None},
 {'key': 'nurbuwat9_13_sidiq', 'name': 'Elang Sidiq', 'description': None},
 {'key': 'nurus_10',
  'name': 'Pangeran Raja Muhammad Nurus, Sultan Kanoman Kaping Sepuluh (10)',
  'description': None}]


EDGES = [('sgj', 'sgj_bratakelana'),
 ('sgj', 'sgj_jayakelana'),
 ('sgj', 'sgj_trusmi'),
 ('sgj', 'sgj_sabakingking'),
 ('sgj', 'sgj_ratu_mas_ayu'),
 ('sgj', 'sgj_ratu_wulung_ayu'),
 ('sgj', 'sgj_pesaraean'),
 ('sgj', 'sgj_ratu_martasari'),
 ('sgj_ratu_wulung_ayu', 'wulung_ratu_agung'),
 ('sgj_ratu_wulung_ayu', 'wulung_pangeran_paseh'),
 ('sgj_ratu_wulung_ayu', 'wulung_pangeran_pekik'),
 ('sgj_ratu_wulung_ayu', 'wulung_pangeran_agung'),
 ('sgj_ratu_wulung_ayu', 'wulung_ratu_wanawati'),
 ('sgj_pesaraean', 'pesaraean_kesatriyan'),
 ('sgj_pesaraean', 'pesaraean_ratu_winaon'),
 ('sgj_pesaraean', 'pesaraean_ratu_emas'),
 ('sgj_pesaraean', 'pesaraean_dipati_anom_carbon'),
 ('sgj_pesaraean', 'pesaraean_panembahan_losari'),
 ('sgj_pesaraean', 'pesaraean_pangeran_waruju'),
 ('sgj_ratu_martasari', 'martasari_pangeran_santri'),
 ('martasari_pangeran_santri', 'santri_prabu_geusan_ulun'),
 ('sedang_kemuning', 'panembahan_ratu_cerbon_kasiji'),
 ('sedang_kemuning', 'sedang_kemuning_pangeran_manis'),
 ('sedang_kemuning', 'sedang_kemuning_pangeran_wirasuta'),
 ('sedang_kemuning', 'sedang_kemuning_ratu_sewuh'),
 ('panembahan_ratu_cerbon_kasiji', 'kasiji_wiranagara'),
 ('panembahan_ratu_cerbon_kasiji', 'kasiji_ratu_ranamanggala'),
 ('panembahan_ratu_cerbon_kasiji', 'kasiji_ratu_singawangun'),
 ('panembahan_ratu_cerbon_kasiji', 'kasiji_tanu_adiarsa'),
 ('panembahan_ratu_cerbon_kasiji', 'kasiji_sedang_belimbing'),
 ('panembahan_ratu_cerbon_kasiji', 'kasiji_arya_kidul'),
 ('panembahan_ratu_cerbon_kasiji', 'kasiji_adipati_sedang_gayam'),
 ('kasiji_adipati_sedang_gayam', 'sedang_gayam_ratu_puteri'),
 ('kasiji_adipati_sedang_gayam', 'girilaya'),
 ('girilaya', 'girilaya_suryaningrat'),
 ('girilaya', 'girilaya_suryamanggala'),
 ('girilaya', 'girilaya_surajaya'),
 ('girilaya', 'girilaya_nataningrat_tanjung_kaling'),
 ('girilaya', 'girilaya_ratu_galampo'),
 ('girilaya', 'girilaya_ratu_katijah'),
 ('girilaya', 'girilaya_pangeran_alas'),
 ('girilaya', 'girilaya_kusumajaya_kajawanan'),
 ('girilaya', 'girilaya_suryadiradiya'),
 ('girilaya', 'girilaya_wangsakerta'),
 ('girilaya', 'badridin_1'),
 ('girilaya', 'girilaya_kartaningrat'),
 ('girilaya', 'girilaya_samsudin_martawijaya'),
 ('badridin_1', 'badridin_01_putera'),
 ('badridin_1', 'badridin_02_mas_rara'),
 ('badridin_1', 'badridin_03_kirana'),
 ('badridin_1', 'badridin_04_arya_lor'),
 ('badridin_1', 'badridin_05_arya_kencana'),
 ('badridin_1', 'badridin_06_arya_kulon'),
 ('badridin_1', 'badridin_07_agung'),
 ('badridin_1', 'badridin_08_godong'),
 ('badridin_1', 'badridin_09_mas_tahjiyah'),
 ('badridin_1', 'badridin_10_arya_kidul'),
 ('badridin_1', 'badridin_11_dipati_kedaton'),
 ('badridin_1', 'badridin_12_kelungsu'),
 ('badridin_1', 'badridin_13_adipati_atanggah'),
 ('badridin_1', 'badridin_14_ampaitan'),
 ('badridin_1', 'badridin_15_adipati_ranamanggala'),
 ('badridin_1', 'badridin_16_adipati_raja_kusuma'),
 ('badridin_1', 'badridin_17_kaprabon_sulaiman'),
 ('badridin_1', 'badridin_18_anggur'),
 ('badridin_1', 'badridin_19_partawijaya'),
 ('badridin_1', 'badridin_20_bagus'),
 ('badridin_1', 'badridin_21_kawisnata'),
 ('badridin_1', 'badridin_22_ahmad'),
 ('badridin_1', 'badridin_23_ratu'),
 ('badridin_1', 'badridin_24_pekik'),
 ('badridin_1', 'badridin_25_duwah'),
 ('badridin_1', 'badridin_26_arya_panengag'),
 ('badridin_1', 'badridin_27_adipati_madengda'),
 ('badridin_1', 'badridin_28_kusuma_ningyun'),
 ('badridin_1', 'badridin_29_rana'),
 ('badridin_1', 'badridin_30_adipati_pringgabaya'),
 ('badridin_1', 'badridin_31_duwet'),
 ('badridin_1', 'badridin_32_raja_kiyandra'),
 ('badridin_1', 'badridin_33_adipati_raja_putra'),
 ('badridin_1', 'kalirudin_2'),
 ('kalirudin_2', 'kalirudin_01_nataningrat'),
 ('kalirudin_2', 'kalirudin_02_surawijaya'),
 ('kalirudin_2', 'kalirudin_03_dipati'),
 ('kalirudin_2', 'kalirudin_04_bonggol'),
 ('kalirudin_2', 'kalirudin_05_martasari'),
 ('kalirudin_2', 'kalirudin_06_ngumar'),
 ('kalirudin_2', 'kalirudin_07_abdul_wali'),
 ('kalirudin_2', 'kalirudin_08_wisu'),
 ('kalirudin_2', 'kalirudin_09_karna'),
 ('kalirudin_2', 'alimudin_3'),
 ('alimudin_3', 'alimudin_01_warok'),
 ('alimudin_3', 'alimudin_02_raja_anom_tangad'),
 ('alimudin_3', 'alimudin_03_jeruk'),
 ('alimudin_3', 'hairidin_4'),
 ('hairidin_4', 'hairidin_01_nuruddin'),
 ('hairidin_4', 'hairidin_02_ngarab_ngorat'),
 ('hairidin_4', 'hairidin_03_cerbon_suni'),
 ('hairidin_4', 'hairidin_04_mandurareja_ngabid'),
 ('hairidin_4', 'hairidin_05_jafarudin'),
 ('hairidin_4', 'hairidin_06_muhayidin'),
 ('hairidin_4', 'hairidin_07_kayudin_ngasikin'),
 ('hairidin_4', 'hairidin_08_ngaripin_ngasidin'),
 ('hairidin_4', 'hairidin_09_muhammad_mangkur'),
 ('hairidin_4', 'hairidin_10_rogawa_suaima'),
 ('hairidin_4', 'hairidin_11_kesatriya_timbul'),
 ('hairidin_4', 'hairidin_12_mundira'),
 ('hairidin_4', 'hairidin_13_kanigara'),
 ('hairidin_4', 'hairidin_14_mangkaradiya'),
 ('hairidin_4', 'hairidin_15_carhizah'),
 ('hairidin_4', 'hairidin_16_kusuma_hasanudin'),
 ('hairidin_4', 'hairidin_17_iskandar'),
 ('hairidin_4', 'hairidin_18_putera_mahmud'),
 ('hairidin_4', 'hairidin_19_bawangin_abu_saat'),
 ('hairidin_4', 'hairidin_20_murti_katifah'),
 ('hairidin_4', 'hairidin_21_ngaripin_sahidin'),
 ('hairidin_4', 'hairidin_22_lakon'),
 ('hairidin_4', 'hairidin_23_jaenidin_farilan'),
 ('hairidin_4', 'hairidin_24_muidah'),
 ('hairidin_4', 'hairidin_25_ailaludin_sangkan'),
 ('hairidin_4', 'hairidin_26_mas_rara_talun'),
 ('hairidin_4', 'hairidin_27_siwi_ngaidah_guntang_a'),
 ('hairidin_4', 'hairidin_28_ambetkasih_safiyah'),
 ('hairidin_4', 'hairidin_29_gubug'),
 ('hairidin_4', 'hairidin_30_mangkarawati_ngafiyah'),
 ('hairidin_4', 'hairidin_31_kaputren'),
 ('hairidin_4', 'hairidin_32_taif'),
 ('hairidin_4', 'hairidin_33_jubaidah'),
 ('hairidin_4', 'hairidin_34_datengpura'),
 ('hairidin_4', 'hairidin_35_kanoman_arilah'),
 ('hairidin_4', 'hairidin_36_somila'),
 ('hairidin_4', 'hairidin_37_pakungdiyah'),
 ('hairidin_4', 'hairidin_38_panengen'),
 ('hairidin_4', 'hairidin_39_pangiwe'),
 ('hairidin_4', 'hairidin_40_hairidin_kacerbonan'),
 ('hairidin_4', 'hairidin_41_atas_angin'),
 ('hairidin_4', 'hairidin_42_juwita_al_dul'),
 ('hairidin_4', 'hairidin_43_murti_maryam'),
 ('hairidin_4', 'hairidin_44_salu'),
 ('hairidin_4', 'hairidin_45_fantara_ngasima'),
 ('hairidin_4', 'hairidin_46_gerage_sangida'),
 ('hairidin_4', 'hairidin_47_jukal'),
 ('hairidin_4', 'hairidin_48_siwi'),
 ('hairidin_4', 'hairidin_49_siwi_ngaidah_guntang_b'),
 ('hairidin_4', 'hairidin_50_saliyu'),
 ('hairidin_4', 'hairidin_51_basiroh'),
 ('hairidin_4', 'hairidin_52_anom_kamil'),
 ('hairidin_4', 'hairidin_53_tisaya_baijah'),
 ('hairidin_4', 'hairidin_54_keraton_rujakah'),
 ('hairidin_4', 'hairidin_55_subita_walung_ngantun'),
 ('hairidin_4', 'hairidin_56_manguntur'),
 ('hairidin_4', 'hairidin_57_mandura_abudin'),
 ('hairidin_4', 'hairidin_58_padmabrata'),
 ('hairidin_4', 'hairidin_59_warsita'),
 ('hairidin_4', 'hairidin_60_riya_kusumanagara'),
 ('hairidin_4', 'imamudin_5'),
 ('imamudin_5', 'imamudin_01_siwulan'),
 ('imamudin_5', 'imamudin_02_kecubung'),
 ('imamudin_5', 'imamudin_03_bonteng'),
 ('imamudin_5', 'imamudin_04_winaon'),
 ('imamudin_5', 'imamudin_05_aimi'),
 ('imamudin_5', 'imamudin_06_jaelani'),
 ('imamudin_5', 'imamudin_07_kulon'),
 ('imamudin_5', 'imamudin_08_walu'),
 ('imamudin_5', 'imamudin_09_brata_pradikta'),
 ('imamudin_5', 'imamudin_10_susilabrata'),
 ('imamudin_5', 'imamudin_11_teratai'),
 ('imamudin_5', 'imamudin_12_partawijaya'),
 ('imamudin_5', 'imamudin_13_susila'),
 ('imamudin_5', 'imamudin_14_tangkulak'),
 ('imamudin_5', 'imamudin_15_sudirga'),
 ('imamudin_5', 'imamudin_16_bogiyah'),
 ('imamudin_5', 'imamudin_17_kaprabon'),
 ('imamudin_5', 'imamudin_18_nakoda'),
 ('imamudin_5', 'kamarudin_6'),
 ('kamarudin_6', 'kamarudin_01_kaprabon'),
 ('kamarudin_6', 'kamarudin_02_rogawa'),
 ('kamarudin_6', 'kamarudin_03_subitaningrat'),
 ('kamarudin_6', 'kamarudin_04_dipati'),
 ('kamarudin_6', 'kamarudin_05_dewi'),
 ('kamarudin_6', 'kamarudin_06_kartaningrat'),
 ('kamarudin_6', 'kamarudin_07_kartawijaya'),
 ('kamarudin_6', 'kamarudin_08_muhammad_cerbon'),
 ('kamarudin_6', 'nurbuwat_7'),
 ('nurbuwat_7', 'nurbuwat7_01_sularaja'),
 ('nurbuwat_7', 'nurbuwat7_02_brataningrat'),
 ('nurbuwat_7', 'nurbuwat7_03_saputra_kalirudin'),
 ('nurbuwat_7', 'nurbuwat7_04_makbul_kartawijaya'),
 ('nurbuwat_7', 'nurbuwat7_05_garambol_ngaisyah'),
 ('nurbuwat_7', 'nurbuwat7_06_waluh_brata_kusuma'),
 ('nurbuwat_7', 'nurbuwat7_07_pulai_giri'),
 ('nurbuwat_7', 'nurbuwat7_08_saliyah'),
 ('nurbuwat_7', 'nurbuwat7_09_arsad_wijayakarta'),
 ('nurbuwat_7', 'nurbuwat7_10_sari_dana'),
 ('nurbuwat_7', 'nurbuwat7_11_rangganingrat'),
 ('nurbuwat_7', 'nurbuwat7_12_anifah'),
 ('nurbuwat_7', 'nurbuwat7_13_raja_diningrat'),
 ('nurbuwat_7', 'nurbuwat7_14_kencana_wungu'),
 ('nurbuwat_7', 'nurbuwat7_15_sulur_bratamadenga'),
 ('nurbuwat_7', 'nurbuwat7_16_raja_kusumaningrat'),
 ('nurbuwat_7', 'nurbuwat7_17_muhammad_dawud'),
 ('nurbuwat_7', 'nurbuwat7_18_siti_rasmi'),
 ('nurbuwat_7', 'nurbuwat7_19_raja_atas_angin'),
 ('nurbuwat_7', 'nurbuwat7_20_raja_cerbon_pangeran'),
 ('nurbuwat_7', 'nurbuwat7_21_raja_cerbon_ratu'),
 ('nurbuwat_7', 'nurbuwat7_22_ratna_adiintan'),
 ('nurbuwat_7', 'nurbuwat7_23_silir_hudayabrata'),
 ('nurbuwat_7', 'nurbuwat7_24_mandapa'),
 ('nurbuwat_7', 'nurbuwat7_25_dzulhaji_prabakusuma'),
 ('nurbuwat_7', 'nurbuwat7_26_siti_fatimah'),
 ('nurbuwat_7', 'nurbuwat7_27_drajat'),
 ('nurbuwat_7', 'nurbuwat7_28_raja_iskandar'),
 ('nurbuwat_7', 'dzulkarnaen_8'),
 ('dzulkarnaen_8', 'dzulkarnaen_01_samsi'),
 ('dzulkarnaen_8', 'dzulkarnaen_02_nawang'),
 ('dzulkarnaen_8', 'dzulkarnaen_03_naam'),
 ('dzulkarnaen_8', 'dzulkarnaen_04_rohani'),
 ('dzulkarnaen_8', 'dzulkarnaen_05_sari_wulan'),
 ('dzulkarnaen_8', 'dzulkarnaen_06_kamam'),
 ('dzulkarnaen_8', 'dzulkarnaen_07_siti_padma'),
 ('dzulkarnaen_8', 'dzulkarnaen_08_suka'),
 ('dzulkarnaen_8', 'dzulkarnaen_09_siti_hadija'),
 ('dzulkarnaen_8', 'dzulkarnaen_10_kusniyah'),
 ('dzulkarnaen_8', 'dzulkarnaen_11_romla'),
 ('dzulkarnaen_8', 'dzulkarnaen_13_gumiwang'),
 ('dzulkarnaen_8', 'dzulkarnaen_14_siyam'),
 ('dzulkarnaen_8', 'dzulkarnaen_15_cahya'),
 ('dzulkarnaen_8', 'dzulkarnaen_16_nurani'),
 ('dzulkarnaen_8', 'dzulkarnaen_17_jaelani_aryadiradeya'),
 ('dzulkarnaen_8', 'nurbuwat_9'),
 ('nurbuwat_9', 'nurbuwat9_01_yusuf'),
 ('nurbuwat_9', 'nurbuwat9_02_husain'),
 ('nurbuwat_9', 'nurbuwat9_03_nurahman'),
 ('nurbuwat_9', 'nurbuwat9_04_nurana'),
 ('nurbuwat_9', 'nurbuwat9_05_ismail'),
 ('nurbuwat_9', 'nurbuwat9_06_nurun'),
 ('nurbuwat_9', 'nurbuwat9_07_yamin'),
 ('nurbuwat_9', 'nurbuwat9_08_rohmani'),
 ('nurbuwat_9', 'nurbuwat9_09_langen'),
 ('nurbuwat_9', 'nurbuwat9_10_nuran'),
 ('nurbuwat_9', 'nurbuwat9_11_jaenab'),
 ('nurbuwat_9', 'nurbuwat9_12_puteri'),
 ('nurbuwat_9', 'nurbuwat9_13_sidiq'),
 ('nurbuwat_9', 'nurus_10')]


# One family group per person who has direct children in the supplied source.
# Order follows the manuscript / edge order.
FAMILY_HEAD_KEYS = []
_seen_heads = set()

for _parent_key, _child_key in EDGES:
    if _parent_key not in _seen_heads:
        _seen_heads.add(_parent_key)
        FAMILY_HEAD_KEYS.append(_parent_key)

del _seen_heads
del _parent_key
del _child_key


# Deterministic IDs used by the previous, now-obsolete whole-tree grouping seed.
LEGACY_GROUP_KEYS = (
    "sunan_gunung_jati",
    "keraton_kanoman",
)


def validate_seed_data() -> None:
    keys = [item["key"] for item in PEOPLE]

    if len(keys) != len(set(keys)):
        raise RuntimeError("Duplicate person key in seed data")

    key_set = set(keys)

    for parent_key, child_key in EDGES:
        if parent_key not in key_set or child_key not in key_set:
            raise RuntimeError(
                f"Edge references unknown person: {parent_key} -> {child_key}"
            )

        if parent_key == child_key:
            raise RuntimeError(f"Self-edge found for {parent_key}")

    if len(FAMILY_HEAD_KEYS) != 18:
        raise RuntimeError(
            "Expected 18 small-family heads from the supplied manuscript, "
            f"found {len(FAMILY_HEAD_KEYS)}"
        )


def seed() -> None:
    validate_seed_data()

    person_by_key = {
        item["key"]: item
        for item in PEOPLE
    }

    key_to_id = {
        item["key"]: stable_uuid("person", item["key"])
        for item in PEOPLE
    }

    created_people = 0
    updated_people = 0
    created_groups = 0
    updated_groups = 0
    removed_legacy_groups = 0
    created_edges = 0
    updated_edges = 0

    try:
        # People must exist before groups because groups reference their head.
        for item in PEOPLE:
            person_id = key_to_id[item["key"]]
            person = db.session.get(
                HistoricalPerson,
                person_id,
            )

            if person is None:
                person = HistoricalPerson(
                    id=person_id
                )
                db.session.add(person)
                created_people += 1
            else:
                updated_people += 1

            person.name = item["name"]
            person.title = None
            person.description = item.get(
                "description"
            )
            person.birth_year = None
            person.death_year = None
            person.location = None
            person.image_url = None
            person.source = SOURCE
            person.is_published = True

        db.session.flush()

        # Remove only the two deterministic seed-owned groups from the old
        # "Sunan Gunung Jati / Keraton Kanoman" grouping approach.
        for legacy_key in LEGACY_GROUP_KEYS:
            legacy_id = stable_uuid(
                "group",
                legacy_key,
            )
            legacy_group = db.session.get(
                HistoricalTreeGroup,
                legacy_id,
            )

            if legacy_group is not None:
                db.session.delete(legacy_group)
                removed_legacy_groups += 1

        db.session.flush()

        # A family group is one head person plus their direct children.
        # Previous/next family connections are derived from global edges.
        for index, head_key in enumerate(
            FAMILY_HEAD_KEYS,
            start=1,
        ):
            head = person_by_key[head_key]
            group_id = stable_uuid(
                "family_group",
                head_key,
            )
            group = db.session.get(
                HistoricalTreeGroup,
                group_id,
            )

            if group is None:
                group = HistoricalTreeGroup(
                    id=group_id
                )
                db.session.add(group)
                created_groups += 1
            else:
                updated_groups += 1

            group.name = f"Keluarga {head['name']}"
            group.head_person_id = key_to_id[head_key]
            group.description = (
                "Keluarga inti berdasarkan anak-anak yang "
                "tercantum langsung dalam naskah sumber."
            )
            group.sort_order = index
            group.is_published = True

        db.session.flush()

        for parent_key, child_key in EDGES:
            edge_key = f"{parent_key}>{child_key}:parent"
            relationship_id = stable_uuid(
                "relationship",
                edge_key,
            )
            relationship = db.session.get(
                HistoricalRelationship,
                relationship_id,
            )

            if relationship is None:
                relationship = HistoricalRelationship(
                    id=relationship_id
                )
                db.session.add(relationship)
                created_edges += 1
            else:
                updated_edges += 1

            relationship.parent_id = key_to_id[parent_key]
            relationship.child_id = key_to_id[child_key]
            relationship.relationship_type = "parent"
            relationship.notes = f"Source: {SOURCE}"

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    print(
        "Historical family seed complete: "
        f"{created_groups} family groups created, "
        f"{updated_groups} family groups updated, "
        f"{removed_legacy_groups} legacy groups removed, "
        f"{created_people} people created, "
        f"{updated_people} people updated, "
        f"{created_edges} relationships created, "
        f"{updated_edges} relationships updated."
    )


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        seed()
