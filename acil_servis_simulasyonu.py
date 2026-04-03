import simpy
import random
import statistics

# İstatistikleri tutacağımız genel sözlük
istatistikler = {
    'Kırmızı': {'bekleme_sureleri': []},
    'Sarı': {'bekleme_sureleri': []},
    'Yeşil': {'bekleme_sureleri': []}
}

class Hastane:
    """Acil servis kaynaklarını ve işlemlerini barındıran sınıf."""
    def __init__(self, env, num_doktor, num_hemsire):
        self.env = env
        # Kritik hastaların sıraya öncelikli girebilmesi için PriorityResource kullanıyoruz
        self.doktorlar = simpy.PriorityResource(env, capacity=num_doktor)
        self.hemsireler = simpy.PriorityResource(env, capacity=num_hemsire)

    def triyaj(self, hasta_adi):
        """Triyaj masasında hemşire değerlendirmesi işlemi."""
        # Triyaj süresi ortalama 3 ile 5 dakika arası sürer
        sure = random.uniform(3, 5)
        yield self.env.timeout(sure)

    def tedavi_et(self, hasta_adi, tedavi_suresi):
        """Doktor tarafından tedavi işlemi."""
        yield self.env.timeout(tedavi_suresi)

def hasta(env, ad, hastane, priorite, kategori, tedavi_suresi):
    """Bir hastanın hastanedeki tüm sürecini simüle eden jeneratör fonksiyonu."""
    gelis_zamani = env.now

    # 1. Aşama: Triyaj
    # Triyaj için de önceliği kullanıyoruz ki, durumu kritik olanlar hemen değerlendirilsin
    with hastane.hemsireler.request(priority=priorite) as hemsire_talebi:
        yield hemsire_talebi
        # Hemşire müsait, triyaj işlemi (kısa sürüyor) başlıyor
        yield env.process(hastane.triyaj(ad))

    # 2. Aşama: Doktor Tedavisi
    # Öncelikli kaynak (PriorityResource) kullanılarak doktor talep ediliyor.
    # Priorite değeri düşük olan (ör: 1 - Kırmızı) sıranın önüne geçer.
    with hastane.doktorlar.request(priority=priorite) as doktor_talebi:
        yield doktor_talebi
        
        # Doktor müsait, tedavi başlıyor
        tedavi_baslangici = env.now
        
        # Toplam bekleme süresi (Geliş anından tedavi başlangıcına kadar geçen süre)
        bekleme_suresi = tedavi_baslangici - gelis_zamani 
        
        # Hastanın test ve bekleme verisini kaydet
        istatistikler[kategori]['bekleme_sureleri'].append(bekleme_suresi)
        
        # Doktor tedavi uyguluyor (randımanlı bir dağılımla hesaplanan tedavi süresi kadar)
        yield env.process(hastane.tedavi_et(ad, tedavi_suresi))

def hasta_gelis_dongusu(env, hastane):
    """Farklı zaman aralıklarında hastaneye hasta gelişini simüle eder."""
    hasta_sayaci = 1
    while True:
        # Hastalar rastgele aralıklarla gelir (örneğin ortalama her 5 dakikada 1 hasta)
        yield env.timeout(random.expovariate(1.0 / 5.0))
        
        # Hasta tipi belirleme (Olasılık dağılımı: %10 Kırmızı, %30 Sarı, %60 Yeşil)
        zar = random.random()
        
        if zar < 0.10:
            kategori = 'Kırmızı'
            priorite = 1  # 1 En Yüksek Öncelik
            # Kırmızı alan hastaları için tedavi süresi uzundur (Ort: 60 dk)
            tedavi_suresi = random.expovariate(1.0 / 60.0)
        elif zar < 0.40:
            kategori = 'Sarı'
            priorite = 2  # 2 Orta Öncelik
            # Sarı alan hastaları için tedavi süresi ortadır (Ort: 30 dk)
            tedavi_suresi = random.expovariate(1.0 / 30.0) 
        else:
            kategori = 'Yeşil'
            priorite = 3  # 3 En Düşük Öncelik
            # Yeşil alan hastaları için tedavi süresi kısadır (Ort: 15 dk)
            tedavi_suresi = random.expovariate(1.0 / 15.0) 
            
        # Hastanın hastane sürecini (yaşam döngüsünü) başlat
        ad = f"Hasta-{hasta_sayaci}"
        env.process(hasta(env, ad, hastane, priorite, kategori, tedavi_suresi))
        hasta_sayaci += 1

def raporla(toplam_sure):
    """Simülasyon bitiminde istatistikleri ve sonuçları ekrana basar."""
    print("=" * 60)
    print(f"ACİL SERVİS SİMÜLASYON RAPORU ({toplam_sure / 60:.1f} Saatlik)")
    print("=" * 60)
    
    toplam_hasta = 0
    toplam_bekleme = 0
    
    for kategori, veriler in istatistikler.items():
        bekleme_listesi = veriler['bekleme_sureleri']
        hasta_sayisi = len(bekleme_listesi)
        toplam_hasta += hasta_sayisi
        
        if hasta_sayisi > 0:
            ortalama_bekleme = statistics.mean(bekleme_listesi)
            max_bekleme = max(bekleme_listesi)
            toplam_bekleme += sum(bekleme_listesi)
        else:
            ortalama_bekleme = 0
            max_bekleme = 0
            
        print(f"--- {kategori} Alan ---")
        print(f"  Tedavi Edilen Hasta : {hasta_sayisi}")
        print(f"  Ortalama Bekleme    : {ortalama_bekleme:.2f} dakika")
        print(f"  Maksimum Bekleme    : {max_bekleme:.2f} dakika\n")
        
    print("=" * 60)
    print(f"Toplam Tedavi Edilen Hasta: {toplam_hasta}")
    if toplam_hasta > 0:
        print(f"Genel Ortalama Bekleme Süresi: {(toplam_bekleme / toplam_hasta):.2f} dakika")
    print("=" * 60)

def simulasyonu_baslat():
    # Rastgelelik için sabit çekirdek (Tekrar üretilebilir sonuçlar için isteğe bağlı)
    # random.seed(42)
    
    # Simülasyon Senaryosu Parametreleri
    KAPASITE_DOKTOR = 3
    KAPASITE_HEMSIRE = 5
    SIMULASYON_SURESI = 1440 # 24 saat (dakika cinsinden)
    
    print("Acil Servis Triyaj Simülasyonu Başlatılıyor...\n(Bu işlem simülasyon ayarlarına göre çok kısa bir sürede tamamlanmaktadır.)\n")
    
    # SimPy ortamını oluştur
    env = simpy.Environment()
    
    # Hastanemizi kur (Doktorlar ve hemşireler)
    hastane = Hastane(env, KAPASITE_DOKTOR, KAPASITE_HEMSIRE)
    
    # Hasta geliş sürecini ortamı ekle
    env.process(hasta_gelis_dongusu(env, hastane))
    
    # Simülasyonu çalıştır (Örn: 24 saat = 1440 dk)
    env.run(until=SIMULASYON_SURESI)
    
    # Simülasyon bittikten sonra sonuçları formatlı şekilde yazdır
    raporla(SIMULASYON_SURESI)

if __name__ == '__main__':
    simulasyonu_baslat()
