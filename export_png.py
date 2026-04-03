import simpy
import random
import pandas as pd
import matplotlib.pyplot as plt
import os

def simulasyon_verisini_hazirla():
    # Rastgelelik için sabit çekirdek (Tekrar üretilebilir sonuçlar için)
    random.seed(42)

    KAPASITE_DOKTOR = 3
    KAPASITE_HEMSIRE = 5
    SIMULASYON_SURESI = 1440 * 2 # 2 Günlük data

    zaman_serisi = []
    aktif_bekleyen = {'Kırmızı': 0, 'Sarı': 0, 'Yeşil': 0}
    tedavi_edilen = {'Kırmızı': 0, 'Sarı': 0, 'Yeşil': 0}
    tedavide_olan = {'Kırmızı': 0, 'Sarı': 0, 'Yeşil': 0}

    class Hastane:
        def __init__(self, env):
            self.env = env
            self.doktorlar = simpy.PriorityResource(env, capacity=KAPASITE_DOKTOR)
            self.hemsireler = simpy.PriorityResource(env, capacity=KAPASITE_HEMSIRE)

    def hasta(env, ad, hastane, priorite, kategori, tedavi_suresi):
        aktif_bekleyen[kategori] += 1
        
        # Triyaj (Hemşire)
        with hastane.hemsireler.request(priority=priorite) as hemsire_talebi:
            yield hemsire_talebi
            yield env.timeout(random.uniform(3, 5))

        # Doktor
        with hastane.doktorlar.request(priority=priorite) as doktor_talebi:
            yield doktor_talebi
            aktif_bekleyen[kategori] -= 1
            tedavide_olan[kategori] += 1
            
            yield env.timeout(tedavi_suresi)
            
            tedavide_olan[kategori] -= 1
            tedavi_edilen[kategori] += 1

    def hasta_gelis_dongusu(env, hastane):
        hasta_sayaci = 1
        while True:
            yield env.timeout(random.expovariate(1.0 / 5.0))
            zar = random.random()
            if zar < 0.10:
                kategori, priorite, tedavi_suresi = 'Kırmızı', 1, random.expovariate(1.0 / 60.0)
            elif zar < 0.40:
                kategori, priorite, tedavi_suresi = 'Sarı', 2, random.expovariate(1.0 / 30.0)
            else:
                kategori, priorite, tedavi_suresi = 'Yeşil', 3, random.expovariate(1.0 / 15.0)
                
            env.process(hasta(env, f"Hasta-{hasta_sayaci}", hastane, priorite, kategori, tedavi_suresi))
            hasta_sayaci += 1

    def veri_toplayici(env):
        while True:
            zaman_serisi.append({
                'Zaman (Dk)': env.now,
                'Bekleyen Kırmızı': aktif_bekleyen['Kırmızı'],
                'Bekleyen Sarı': aktif_bekleyen['Sarı'],
                'Bekleyen Yeşil': aktif_bekleyen['Yeşil'],
                'Taburcu Kırmızı': tedavi_edilen['Kırmızı'],
                'Taburcu Sarı': tedavi_edilen['Sarı'],
                'Taburcu Yeşil': tedavi_edilen['Yeşil'],
            })
            yield env.timeout(1)

    env = simpy.Environment()
    hastane = Hastane(env)
    env.process(hasta_gelis_dongusu(env, hastane))
    env.process(veri_toplayici(env))
    env.run(until=SIMULASYON_SURESI)

    return pd.DataFrame(zaman_serisi)

def grafik_olustur():
    print("Simülasyon koşturuluyor... Lütfen bekleyin.")
    df = simulasyon_verisini_hazirla()
    
    # Grafik oluşturma metodu
    plt.figure(figsize=(12, 10))
    
    # 1. Grafik
    plt.subplot(2, 1, 1)
    plt.plot(df['Zaman (Dk)'], df['Bekleyen Kırmızı'], color='red', label='Bekleyen Kırmızı')
    plt.plot(df['Zaman (Dk)'], df['Bekleyen Sarı'], color='gold', label='Bekleyen Sarı')
    plt.plot(df['Zaman (Dk)'], df['Bekleyen Yeşil'], color='green', label='Bekleyen Yeşil')
    plt.title('Acil Serviste Anlık Bekleyen Hasta Sayıları (2 Günlük Kesit)', fontsize=14, fontweight='bold')
    plt.xlabel('Zaman (Dakika)', fontsize=12)
    plt.ylabel('Bekleyen Hasta', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # 2. Grafik
    plt.subplot(2, 1, 2)
    plt.plot(df['Zaman (Dk)'], df['Taburcu Kırmızı'], color='red', linestyle='-', label='Taburcu Kırmızı')
    plt.plot(df['Zaman (Dk)'], df['Taburcu Sarı'], color='gold', linestyle='-', label='Taburcu Sarı')
    plt.plot(df['Zaman (Dk)'], df['Taburcu Yeşil'], color='green', linestyle='-', label='Taburcu Yeşil')
    plt.title('Kümülatif Taburcu Edilen Hasta Sayısı', fontsize=14, fontweight='bold')
    plt.xlabel('Zaman (Dakika)', fontsize=12)
    plt.ylabel('Taburcu Edilen Hasta', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Daha şık bir görünüm için grafikler arası boşluk ayarlama
    plt.tight_layout(pad=3.0)
    
    # Kaydetme işlemi
    out_file = "acil_servis_grafikleri.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight')
    print(f"Grafikler '{out_file}' olarak başarıyla kaydedildi!")

if __name__ == '__main__':
    grafik_olustur()
