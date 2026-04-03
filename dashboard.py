import streamlit as st
import simpy
import random
import time
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Canlı Acil Servis Triyaj Sistemi", layout="wide")

st.title("🏥 Canlı Acil Servis Triyaj Simülasyonu")
st.markdown("Arka planda SimPy simülasyonu koşturulur ve sonuçları saniye saniye Dashboard (Dashport) olarak size canlı sunulur.")

# Simülasyon Ön Düzenlemesi (Veri Önbellekleme)
@st.cache_data
def simulasyon_verisini_hazirla():
    # Rastgelelik için sabit çekirdek (Tekrar üretilebilir sonuçlar için)
    random.seed(42)

    KAPASITE_DOKTOR = 3
    KAPASITE_HEMSIRE = 5
    SIMULASYON_SURESI = 1440 * 2 # 2 Günlük data simüle edelim ki ekranda akıcı ve uzun gözüksün

    # Zaman çizelgesi verileri (her dakika için kaydedilecek)
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
        """Her dakikada bir sistemin fotoğrafını çeker ve loglar."""
        while True:
            zaman_serisi.append({
                'Zaman (Dk)': env.now,
                'Bekleyen Kırmızı': aktif_bekleyen['Kırmızı'],
                'Bekleyen Sarı': aktif_bekleyen['Sarı'],
                'Bekleyen Yeşil': aktif_bekleyen['Yeşil'],
                'Tedavideki Kırmızı': tedavide_olan['Kırmızı'],
                'Tedavideki Sarı': tedavide_olan['Sarı'],
                'Tedavideki Yeşil': tedavide_olan['Yeşil'],
                'Taburcu Kırmızı': tedavi_edilen['Kırmızı'],
                'Taburcu Sarı': tedavi_edilen['Sarı'],
                'Taburcu Yeşil': tedavi_edilen['Yeşil'],
            })
            yield env.timeout(1)

    # Simülasyonu çalıştır ve veriyi topla
    env = simpy.Environment()
    hastane = Hastane(env)
    env.process(hasta_gelis_dongusu(env, hastane))
    env.process(veri_toplayici(env))
    env.run(until=SIMULASYON_SURESI)

    return pd.DataFrame(zaman_serisi)

# Veriyi bir defa oluştur ve kullan
df = simulasyon_verisini_hazirla()

# UI Elemanları (Hız Kontrolü)
col_kontrol1, col_kontrol2 = st.columns(2)
with col_kontrol1:
    simulasyon_hizi = st.slider("Simülasyon Oynatma Hızı (Dakika Atlanır)", 1, 60, 10)
with col_kontrol2:
    baslat = st.button("Simülasyonu Başa Sar ve Oynat")

if baslat or 'current_step' not in st.session_state:
    st.session_state.current_step = 0

# Ekranı üçe bölüp metrikleri koyalım
col1, col2, col3 = st.columns(3)
kirmizi_metric = col1.empty()
sari_metric = col2.empty()
yesil_metric = col3.empty()

zaman_metric = st.empty()
chart_placeholder = st.empty()

# Eğer başlatılmışsa ve sınırları aşmadıysa animasyonu çalıştır
if st.session_state.current_step < len(df):
    for i in range(st.session_state.current_step, len(df), simulasyon_hizi):
        current_data = df.iloc[i]
        historic_data = df.iloc[:i+1]
        
        # Saniye değil Dakika Dönüşümü
        dakika = int(current_data['Zaman (Dk)'])
        saat = (dakika // 60) % 24
        gun = (dakika // 1440) + 1
        kalan_dakika = dakika % 60
        
        zaman_metric.markdown(f"### 🕒 Simülasyon Saati: Gün {gun} - Saat {saat:02d}:{kalan_dakika:02d}")
        
        kirmizi_metric.metric("🔴 Kırmızı Alan (Kritik)", 
                              f"Bekleyen: {int(current_data['Bekleyen Kırmızı'])}",
                              f"Taburcu: {int(current_data['Taburcu Kırmızı'])}")
        sari_metric.metric("🟡 Sarı Alan (Acil)", 
                           f"Bekleyen: {int(current_data['Bekleyen Sarı'])}",
                           f"Taburcu: {int(current_data['Taburcu Sarı'])}")
        yesil_metric.metric("🟢 Yeşil Alan (Hafif)", 
                            f"Bekleyen: {int(current_data['Bekleyen Yeşil'])}",
                            f"Taburcu: {int(current_data['Taburcu Yeşil'])}")
        
        # Geçmişe dönük Çizgi grafiğini güncelle
        chart_data = historic_data[['Zaman (Dk)', 'Bekleyen Kırmızı', 'Bekleyen Sarı', 'Bekleyen Yeşil']].set_index('Zaman (Dk)')
        chart_placeholder.line_chart(chart_data, color=["#FF0000", "#FFD700", "#008000"])
        
        time.sleep(0.05)
        st.session_state.current_step = i
