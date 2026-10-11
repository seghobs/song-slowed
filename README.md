# Tempo Studio

MP3 ve WAV şarkıları ses perdesini koruyarak 0.50–2.00× hız aralığında işler. Vokal ve enstrümanlar birlikte işlenir; kaynak örnekleme hızı korunur.

## Şarkıya göre profil ve A/B karşılaştırma

Otomatik öneri, tüm kayıt boyunca düşük örnekleme hızlı merkez/yan enerji ölçümü yapar. Ölçüm stereo düzeni içindir; şarkı türünü veya işitsel kaliteyi kesin olarak tespit etmez. Merkez enerji payı %65 ve üstündeyse merkez odak, diğer durumda geniş stereo önerilir. Analiz için düşürülen örnekleme hızı yalnızca ölçüm kopyasındadır; işlenen kaydın kaynak örnekleme hızı korunur.

- Vokal / merkez odak: R3 `--centre-focus`; merkez sesler ve mono uyumluluğunu önceliklendirir.
- Enstrümantal / geniş stereo: R3 varsayılan bağımsız kanal modu; stereo kanalların ayrıntılarını önceliklendirir. Merkez odakla karşılaştırarak seçin.
- İki profil de tam kaliteli offline R3 kullanır; R3'te etkisiz olan R2 transient/window seçenekleriyle sahte profiller yaratılmaz.

A/B karşılaştırma gerçek indirilebilir çıktı ile orijinali dinletir. Orijinal 1×, çıktı seçilen hızda oynar. Orijinaldeki `t` noktası çıktıda `t / hız` noktasına eşlenir; bu müzik konumu eşlemesidir, iki dalga biçiminin örnek düzeyinde özdeşliği değildir. Bölüm döngüsü sınırları orijinal saniyesindedir. Döngü ve A/B geçişleri tarayıcı ses oynatıcısıyla yapılır; örnek hassasiyetinde değildir. Ortak ses seviyesi her iki oynatıcıya aynı volume değerini verir; loudness normalizasyonu uygulamaz.

FLAC ve float WAV karşılaştırma kopyası, nihai dosya tekrar tempo işleminden geçirilmeden 24 bit WAV'a çözülür. İndirilebilir dosya korunur. Dinleme kopyaları için 1 GB yükleme sınırı vardır. Dosya RAM'de cevap olarak tutulduğundan çok uzun kayıtlar için yeterli RAM/disk gerekir.

## Motor ve dışa aktarma

### İki profili birlikte oluşturma

"İki profili oluştur" işlemi aynı girdi, hız ve çıktı formatıyla hem merkez odak hem geniş stereo sonucunu üretir. Başlangıç tercihi ilk dinlenecek profili belirler; otomatik tercih analiz önerisini kullanır. Her iki sonuç ve dinleme kopyaları tarayıcıda hazır tutulur. B (merkez odak) / C (geniş stereo) arasında geçişte tempo ve müzik konumu korunur; yeni sunucu işlemi veya yükleme yapılmaz. A orijinali dinletir. Native tarayıcı oynatıcısı kullanıldığı için geçişte çok kısa seek gecikmesi olabilir; örnek hassasiyetinde kesintisiz geçiş garantisi yoktur.

"Dinlediğim profili seç" indirilecek sonucu belirler. Dinleme profilini değiştirmek seçilen indirme tercihini değiştirmez. Dosya adı seçilen profili içerir. Yeni dosya veya yeni işleme eski iki sonucu temizler. İki sonuç oluşturulması işlem süresini ve tarayıcı RAM kullanımını artırır.

- Rubber Band 4.0.0 R3/Finer motoru; gerçek zamanlı veya draft modu yerine tüm dosyayı analiz eden offline işleme.
- Merkez odak modu: stereo vokal konumu ve mono uyumluluğu için `--centre-focus`.
- 32 bit float ara dosyalar; tempo değişirken frekans katsayısı 1.0.
- 1.00× hızda time stretching atlanır. EQ, gürültü giderme veya loudness normalizasyonu uygulanmaz. R3 aracı işleme kaynaklı clipping saptarsa kendi korumasıyla kazancı azaltabilir.
- WAV 24 bit: genel dinleme için önerilen. FLAC 24 bit: kayıpsız sıkıştırma. WAV 32 bit float: sonraki düzenleme için yüksek hassasiyet (bazı tarayıcılarda önizleme desteklenmeyebilir). MP3: 320 kbps, LAME compression_level=0; kayıplı bir formattır.
- 24 bit çıktıda üçgensel dither uygulanır. Örnekleme hızı yapay olarak yükseltilmez; 32 bit çıktı kaynakta bulunmayan detayları geri getirmez.

## Başlatma

### Windows: tek tıkla kur ve çalıştır

1. GitHub'da **Code → Download ZIP** ile projeyi indirin veya klonlayın.
2. ZIP'i tamamen bir klasöre çıkarın. ZIP içinden çalıştırmayın.
3. **`start.bat` dosyasına çift tıklayın.** İlk çalıştırmada eksik araçlar ve Python paketleri otomatik kurulur; hazır olduğunda tarayıcı açılır.

Windows 10/11 64 bit gerekir. İlk kurulum internet bağlantısı gerektirir ve birkaç dakika sürebilir. Uyumlu Python 3.10–3.13 ve FFmpeg varsa kullanılır. Yoksa resmi, imzası doğrulanan Python 3.13.12 yükleyicisi uygulamanın `tools/python` klasörüne kullanıcı düzeyinde kurulum yapar; FFmpeg Gyan Windows paketinden indirilip SHA256 ile doğrulanır. Rubber Band 4.0.0 da resmi paketten SHA256 doğrulamasıyla kurulur. Global Python paketleri değiştirilmez; uygulama paketleri `.venv` içine kurulur. Sistem PATH'i kalıcı olarak değiştirilmez.

Sonraki açılışlar kurulumu tekrar indirmez. Paket listesi değiştiğinde güncellenir; bozuk uygulama ortamı yeniden oluşturulur. Kurulumda hata olursa pencere açık kalır ve nedenini gösterir; tamamlanan aşamalar sonraki denemede tekrar kullanılabilir. Windows'un güvenlik bildirimi veya kurumsal cihaz kısıtlaması ayrıca kullanıcı işlemi gerektirebilir.

Sunucu arka planda çalışır; açılış penceresini kapatabilirsiniz. **`stop.bat`** yalnızca bu başlatıcının açtığı Tempo Studio sunucusunu durdurur. Zaten açıksa ikinci sunucu başlatılmaz. 8765 doluysa 8785'e kadar uygun bir yerel port seçilir ve tarayıcı doğru adrese açılır. Sunucu yalnızca bilgisayarın kendi bağlantısından (`127.0.0.1`) erişilebilir.

Günlükler `.runtime/server.log` ve `.runtime/server-error.log` içinde bulunur. `.venv`, `.runtime` ve indirilen araçlar Git'e dahil değildir. Uygulama klasörünü taşıdıysanız başlatıcı çalışmayan ortamı yedekleyip yeniden kurar.

### Elle kurulum / diğer sistemler

Python 3.10+, FFmpeg ve Rubber Band 3+ komut satırı aracı gerekir. Windows için `setup-rubberband.ps1` resmi Rubber Band 4.0.0 paketini indirir, SHA256 doğrulaması yapar ve lisansı ile `tools/rubberband/` içine kurar. İndirilen üçüncü taraf dosyalar ve yerel test ekran görüntüleri Git deposuna dahil değildir. Diğer sistemlerde `rubberband` komutunu PATH'e kurun. R3 motoru yoksa uygulama düşük kaliteli bir motora sessizce geçmez.

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\setup-rubberband.ps1
python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

http://127.0.0.1:8765 adresini açın. Flask alternatifi: `python flask_app.py`. İki sunucuyu aynı portta birlikte başlatmayın. Otomatik başlatıcı FastAPI kullanır.

Dosyalar bilgisayarda işlenir, geçici dosyalar işlem sonunda silinir. 150 MB sınırı ve her işleme adımında 20 dakika zaman aşımı vardır. Bu yerel kullanım sürümüdür.

Rubber Band time stretching uygular; frekans katsayısı 1 ile perde korunur. Özellikle aşırı hızlarda geçişler ve ses dokusunda işleme izleri oluşabilir. Tamamen artifactsız sonuç garantisi verilmez. 0.8–1.2× aralığında kendi şarkınızla dinleyerek karşılaştırın. Vokal ayrıştırma uygulanmaz; ayrıştırma ayrıca ses kayıpları yaratabileceğinden tüm miks birlikte işlenir.

Kaynak: https://breakfastquay.com/rubberband/ ve https://breakfastquay.com/news/20220707.html

İndirilen resmi Windows paketi: https://breakfastquay.com/files/releases/rubberband-4.0.0-gpl-executable-windows.zip
Üçüncü taraf lisansı: `tools/rubberband/rubberband-4.0.0-gpl-executable-windows/COPYING.txt`.

Doğrulama: `python -m unittest discover -s tests -v` (testler NumPy gerektirir).

Geliştirme testleri için `python -m pip install -r requirements-dev.txt` kullanın. Windows başlatıcısını tarayıcı açmadan çalıştırmak için `powershell -NoProfile -ExecutionPolicy Bypass -File .\launch.ps1 -NoBrowser`, sadece kurulum kontrolü için `-SetupOnly` ekleyin. `-ForcePortable` ilk kurulumda mevcut sistem Python/FFmpeg'ini kullanmadan yerel araçları kurmayı sağlar.

Karşılaştırma zaman eşleme testleri: `node tests/test_timeline.cjs`.

Testler 0.5–2× hızlarda perde/süreyi, 48 kHz stereo kanal ayrımını, dört çıktı formatını, MP3 girdisini ve 1× float çıktının kaynak örneklerle birebir eşitliğini kontrol eder. Bunlar gerçek bir şarkıda işitsel kalite garantisi yerine geçmez.
