import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk

# --- VERİTABANI YÖNETİMİ (SQLite) ---
class Database:
    def __init__(self, db_name="dolap_envanter.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS urunler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isim TEXT NOT NULL,
                bolme INTEGER NOT NULL,
                kategori TEXT,
                adet INTEGER,
                birim TEXT,
                aciklama TEXT
            )
        """
        )
        self.conn.commit()

    def urun_ekle(self, isim, bolme, kategori, adet, birim, aciklama):
        self.cursor.execute(
            """
            INSERT INTO urunler (isim, bolme, kategori, adet, birim, aciklama)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (isim, bolme, kategori, adet, birim, aciklama),
        )
        self.conn.commit()

    def urunleri_getir(self, arama="", bolme_filtre=None):
        query = "SELECT * FROM urunler WHERE 1=1"
        params = []
        if arama:
            query += " AND (isim LIKE ? OR kategori LIKE ? OR aciklama LIKE ?)"
            params.extend([f"%{arama}%", f"%{arama}%", f"%{arama}%"])
        if bolme_filtre is not None:
            query += " AND bolme = ?"
            params.append(bolme_filtre)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def urun_sil(self, urun_id):
        self.cursor.execute("DELETE FROM urunler WHERE id = ?", (urun_id,))
        self.conn.commit()


# --- ANA UYGULAMA ARAYÜZÜ ---
class EnvanterApp(ctk.CTk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.selected_bolme = 1  # Varsayılan seçili bölme

        self.title("12 Bölmeli Dolap Envanter Takip Sistemi")
        self.geometry("1100x700")
        
        # Tema Ayarı
        ctk.set_appearance_mode("System")  # Dark / Light
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_content()
        self.tablo_guncelle()

    def create_sidebar(self):
        # Sol Panel: Bölme Seçim ve Ekleme Formu
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # Başlık
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="📦 Dolap Envanteri", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # 1. Bölme Seçim Alanı (Görsel Buton Izgarası)
        self.lbl_bolme_sec = ctk.CTkLabel(self.sidebar_frame, text="Hedef Bölme Seçin:", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_bolme_sec.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="w")

        self.bolme_grid_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.bolme_grid_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.bolme_buttons = []
        for i in range(1, 13):
            btn = ctk.CTkButton(
                self.bolme_grid_frame, text=str(i), width=50, height=35,
                command=lambda b=i: self.set_bolme(b)
            )
            # 4 sütunlu yerleşim
            row = (i - 1) // 4
            col = (i - 1) % 4
            btn.grid(row=row, column=col, padx=3, pady=3)
            self.bolme_buttons.append(btn)
        
        self.highlight_bolme_button(1)

        # Form Alanları
        self.entry_isim = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Ürün Adı (örn: M3 Vida)")
        self.entry_isim.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="ew")

        self.entry_kategori = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Kategori (örn: Hırdavat)")
        self.entry_kategori.grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        # Miktar ve Birim Yan Yana
        self.miktar_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.miktar_frame.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        self.miktar_frame.grid_columnconfigure(0, weight=2)
        self.miktar_frame.grid_columnconfigure(1, weight=1)

        self.entry_adet = ctk.CTkEntry(self.miktar_frame, placeholder_text="Miktar")
        self.entry_adet.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.combo_birim = ctk.CTkComboBox(self.miktar_frame, values=["Adet", "Paket", "Metre", "Gram", "Set"])
        self.combo_birim.grid(row=0, column=1, sticky="ew")
        self.combo_birim.set("Adet")

        self.entry_aciklama = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Açıklama / Not (opsiyonel)")
        self.entry_aciklama.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        # Kaydet Butonu
        self.btn_kaydet = ctk.CTkButton(
            self.sidebar_frame, text="➕ Ürünü Dolaba Ekle", fg_color="#2fa572", hover_color="#248259",
            command=self.urun_ekle_aksiyon, height=40, font=ctk.CTkFont(size=14, weight="bold")
        )
        self.btn_kaydet.grid(row=7, column=0, padx=20, pady=(15, 10), sticky="ew")

    def create_main_content(self):
        # Sağ Panel: Arama, Filtreleme ve Tablo Listesi
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Üst Araç Çubuğu (Arama ve Filtreleme)
        self.toolbar_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.toolbar_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.toolbar_frame.grid_columnconfigure(0, weight=1)

        self.entry_arama = ctk.CTkEntry(self.toolbar_frame, placeholder_text="🔍 Dolapta ürün ara (isim, kategori, açıklama)...", height=38)
        self.entry_arama.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry_arama.bind("<KeyRelease>", lambda e: self.tablo_guncelle())

        self.btn_tumunu_goster = ctk.CTkButton(
            self.toolbar_frame, text="Tümünü Göster", width=120, height=38,
            command=self.filtresi_sifirla
        )
        self.btn_tumunu_goster.grid(row=0, column=1)

        # Aktif Durum Bilgisi
        self.lbl_durum = ctk.CTkLabel(self.main_frame, text="Tüm Bölmeler Listeleniyor", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_durum.grid(row=1, column=0, sticky="w", pady=(0, 5))

        # Tablo (Treeview)
        self.tree_frame = ctk.CTkFrame(self.main_frame)
        self.tree_frame.grid(row=2, column=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28, font=("Arial", 11))
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))

        columns = ("ID", "İsim", "Bölme", "Kategori", "Miktar", "Açıklama")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        
        col_widths = [40, 200, 70, 130, 90, 300]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="w" if col != "ID" and col != "Bölme" else "center")

        self.tree.grid(row=0, column=0, sticky="nsew")

        # Kaydırma Çubuğu
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Sağ Alt Silme Butonu
        self.btn_sil = ctk.CTkButton(
            self.main_frame, text="🗑️ Seçili Ürünü Sil", fg_color="#d9534f", hover_color="#c9302c",
            command=self.urun_sil_aksiyon, height=35
        )
        self.btn_sil.grid(row=3, column=0, sticky="e", pady=(15, 0))

    def set_bolme(self, bolme_no):
        self.selected_bolme = bolme_no
        self.highlight_bolme_button(bolme_no)
        # Bölmeye tıklandığında direkt o bölmenin filtrelemesini de yapabiliriz veya sadece hedef yapabiliriz.
        # Burada hem hedef seçiyoruz hem de tabloyu o bölmeye filtreliyoruz:
        self.lbl_durum.configure(text=f"Filtre: Bölme {bolme_no} İçeriği")
        self.tablo_guncelle(bolme_filtre=bolme_no)

    def highlight_bolme_button(self, aktif_no):
        for i, btn in enumerate(self.bolme_buttons):
            if i + 1 == aktif_no:
                btn.configure(fg_color="#1f538d", border_width=2, border_color="white")
            else:
                btn.configure(fg_color=("#3b8ed0", "#1f6aa5"), border_width=0)

    def filtresi_sifirla(self):
        self.entry_arama.delete(0, "end")
        self.lbl_durum.configure(text="Tüm Bölmeler Listeleniyor")
        self.tablo_guncelle(bolme_filtre=None)

    def urun_ekle_aksiyon(self):
        isim = self.entry_isim.get().strip()
        kategori = self.entry_kategori.get().strip()
        adet_str = self.entry_adet.get().strip()
        birim = self.combo_birim.get()
        aciklama = self.entry_aciklama.get().strip()

        if not isim:
            messagebox.showwarning("Eksik Bilgi", "Lütfen ürün adını giriniz.")
            return

        try:
            adet = int(adet_str) if adet_str else 1
        except ValueError:
            messagebox.showerror("Hatalı Değer", "Miktar alanı sadece sayısal değer alabilir.")
            return

        # Veritabanına kayıt
        self.db.urun_ekle(isim, self.selected_bolme, kategori, adet, birim, aciklama)

        # Formu temizle
        self.entry_isim.delete(0, "end")
        self.entry_kategori.delete(0, "end")
        self.entry_adet.delete(0, "end")
        self.entry_aciklama.delete(0, "end")

        # Tabloyu tazele
        self.tablo_guncelle(bolme_filtre=self.selected_bolme)
        messagebox.정보("Başarılı", f"Ürün başarıyla Bölme {self.selected_bolme}'ye eklendi!")

    def urun_sil_aksiyon(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Seçim Yok", "Lütfen silmek istediğiniz ürünü tablodan seçin.")
            return

        item_values = self.tree.item(selected_item, "values")
        urun_id = item_values[0]

        if messagebox.askyesno("Onay", f"'{item_values[1]}' isimli ürünü silmek istediğinize emin misiniz?"):
            self.db.urun_sil(urun_id)
            self.tablo_guncelle()

    def tablo_guncelle(self, bolme_filtre=None):
        for row in self.tree.get_children():
            self.tree.delete(row)

        arama_metni = self.entry_arama.get().strip()
        
        # Eğer özel filtre gelmediyse ve arama kutusu doluysa her yerde ara
        kayitlar = self.db.urunleri_getir(arama=arama_metni, bolme_filtre=bolme_filtre)

        for kayit in kayitlar:
            # kayit = (id, isim, bolme, kategori, adet, birim, aciklama)
            formatted_adet = f"{kayit[4]} {kayit[5]}"
            self.tree.insert("", "end", values=(kayit[0], kayit[1], f"Bölme {kayit[2]}", kayit[3], formatted_adet, kayit[6]))


if __name__ == "__main__":
    db = Database()
    app = EnvanterApp(db)
    app.mainloop()