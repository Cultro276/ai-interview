"""
Role-based situational prompt catalog for common positions in TR market.

Each role contains:
- key: machine-friendly identifier
- titles: synonyms/variants used in job ads
- competencies: core competencies to target
- scenarios: role-specific situational question starters
"""

from __future__ import annotations

ROLE_PROMPTS: list[dict[str, object]] = [
    {
        "key": "retail_sales_consultant",
        "titles": [
            "satış danışmanı", "mağaza satış danışmanı", "retail sales associate", "perakende satış"
        ],
        "competencies": ["Müşteri ilişkileri", "İtiraz karşılama", "Up-sell/Cross-sell", "Stok & görsel"],
        "scenarios": [
            "Müşteri fiyatı yüksek buluyor ve ayrılmak üzere. Nasıl yaklaşırsınız?",
            "İade politikaya uymuyor, müşteri ısrarcı. Durumu nasıl yönetirsiniz?",
            "Yoğun kampanya gününde kasa kuyruğu uzadı. Öncelikleri nasıl belirlersiniz?",
        ],
    },
    {
        "key": "store_manager",
        "titles": ["mağaza müdürü", "store manager"],
        "competencies": ["Ekip yönetimi", "Hedef takibi", "Vardiya & planlama", "Müşteri memnuniyeti"],
        "scenarios": [
            "Satış hedefleri geride. 2 hafta içinde toparlamak için planınız ne olur?",
            "Ekipte yüksek devinim var. Rotasyon ve eğitimle nasıl çözersiniz?",
            "Stok sayım farkı tespit edildi. Soruşturmayı nasıl yürütürsünüz?",
        ],
    },
    {
        "key": "call_center_agent",
        "titles": ["çağrı merkezi", "müşteri temsilcisi", "call center", "call-center"],
        "competencies": ["Empati", "Itiraz yönetimi", "Net iletişim", "İkna"],
        "scenarios": [
            "Çok öfkeli bir müşteri hattı meşgul ediyor. Nasıl yatıştırır ve sonuca gidersiniz?",
            "İlk aramada çözemediğiniz talebi nasıl takip edersiniz?",
            "SLA ihlali riski var. Hangi adımları önceliklendirirsiniz?",
        ],
    },
    {
        "key": "customer_success",
        "titles": ["müşteri başarı", "customer success", "müşteri deneyimi"],
        "competencies": ["Proaktif takip", "Değer sunumu", "Churn önleme", "İletişim"],
        "scenarios": [
            "Kullanım düşüşü gördüğünüz bir müşteriyi nasıl kurtarırsınız?",
            "Yeni modülü benimsetmek için planınız ne olur?",
            "Yıllık yenileme görüşmesinde risk var. Stratejiniz?",
        ],
    },
    {
        "key": "operations_specialist",
        "titles": ["operasyon uzmanı", "operation specialist"],
        "competencies": ["Süreç", "Koordinasyon", "Problem çözme", "Önceliklendirme"],
        "scenarios": [
            "Teslimatlarda gecikme zinciri oluştu. Kök nedeni nasıl bulur ve aksiyon alırsınız?",
            "Birden fazla departmanla çakışan istekleri nasıl koordine edersiniz?",
            "Beklenmedik hacim artışında kapasiteyi nasıl yönetirsiniz?",
        ],
    },
    {
        "key": "logistics_specialist",
        "titles": ["lojistik uzmanı", "lojistik planlama", "logistics"],
        "competencies": ["Rota & planlama", "Maliyet", "Tedarikçi yönetimi", "SLA"],
        "scenarios": [
            "Araç arızasıyla kritik sevkiyat gecikti. Alternatif planınız nedir?",
            "Nakliye maliyetleri yükseldi. Optimizasyon yaklaşımınız?",
            "Depo-stok arasında sayım farkı. Nasıl araştırırsınız?",
        ],
    },
    {
        "key": "procurement_specialist",
        "titles": ["satınalma uzmanı", "tedarik uzmanı", "procurement"],
        "competencies": ["Müzakere", "Tedarikçi değerlendirme", "Maliyet", "Sözleşme"],
        "scenarios": [
            "Kritik kalemde tek tedarikçiye bağımlılık var. Riskinizi nasıl düşürürsünüz?",
            "Kur dalgalanmasında maliyetleri nasıl sabitlersiniz?",
            "Kalite düşüşü şikayeti geldi. Tedarikçi ile nasıl yönetirsiniz?",
        ],
    },
    {
        "key": "hr_specialist",
        "titles": ["ik uzmanı", "insan kaynakları uzmanı", "hr specialist"],
        "competencies": ["İşe alım", "Uygunluk", "Performans", "Çalışan ilişkileri"],
        "scenarios": [
            "Acil işe alımda aday havuzu zayıf. Pipeline'ı nasıl güçlendirirsiniz?",
            "Disiplin süreci gereken bir durumla nasıl ilerlersiniz?",
            "Onboarding’de ilk 90 gün için planınız nedir?",
        ],
    },
    {
        "key": "recruiter",
        "titles": ["işe alım uzmanı", "recruiter", "talent acquisition"],
        "competencies": ["Sourcing", "Screening", "Stakeholder management", "Offer"],
        "scenarios": [
            "Zor bulunan rolde pasif adayları nasıl çekersiniz?",
            "Hiring manager ile kalibrasyon uyuşmuyor. Nasıl hizalarsınız?",
            "Kabul oranını artırmak için teklif stratejiniz?",
        ],
    },
    {
        "key": "accounting_specialist",
        "titles": ["muhasebe uzmanı", "muhasebe elemanı", "accounting"],
        "competencies": ["Tek düzen", "Mutabakat", "Fatura & tahsilat", "Dönem sonu"],
        "scenarios": [
            "Banka mutabakatlarında açıklanamayan fark. Nasıl araştırırsınız?",
            "Yoğun dönem kapanışında iş dağılımını nasıl yönetirsiniz?",
            "E-fatura iade/iptal süreç sorunlarını nasıl çözersiniz?",
        ],
    },
    {
        "key": "finance_specialist",
        "titles": ["finans uzmanı", "finansal analiz", "treasury"],
        "competencies": ["Nakit akışı", "Bütçe", "Raporlama", "Risk"],
        "scenarios": [
            "Nakit açığı öngörülüyor. Kısa vadeli planınız?",
            "Bütçe sapmalarını nasıl analiz eder ve raporlarsınız?",
            "Kur riski artışına karşı ne yaparsınız?",
        ],
    },
    {
        "key": "backend_developer",
        "titles": ["yazılım geliştirici", "backend developer", "python developer", "java developer"],
        "competencies": ["API", "Veritabanı", "Ölçeklenebilirlik", "Observability"],
        "scenarios": [
            "Production'da kritik performans sorunu. Root-cause analizi ve çözümünüz?",
            "Veritabanı migrasyonunda kesintisiz geçişi nasıl planlarsınız?",
            "Kırılgan bir modülü nasıl refactor edersiniz?",
        ],
    },
    {
        "key": "frontend_developer",
        "titles": ["frontend developer", "react developer", "web geliştirici"],
        "competencies": ["UI/UX", "Performans", "Erişilebilirlik", "State management"],
        "scenarios": [
            "Yavaşlanan bir sayfayı nasıl profiler ve optimize edersiniz?",
            "Design sistemine uymayan legacy sayfayı nasıl dönüştürürsünüz?",
            "CSR/SSR sorununda SEO kaybını nasıl giderirsiniz?",
        ],
    },
    {
        "key": "mobile_developer",
        "titles": ["mobil geliştirici", "android developer", "ios developer", "react native"],
        "competencies": ["Performans", "Offline", "Store süreçleri", "Crash analizi"],
        "scenarios": [
            "Kritik crash oranı arttı. Nasıl tespit ve çözersiniz?",
            "Offline senaryosu için veri eşitlemeyi nasıl kurgularsınız?",
            "Store reddini nasıl analiz edip düzeltirsiniz?",
        ],
    },
    {
        "key": "qa_engineer",
        "titles": ["qa mühendisi", "test mühendisi", "quality assurance"],
        "competencies": ["Test stratejisi", "Otomasyon", "Regresyon", "Hata yönetimi"],
        "scenarios": [
            "Regresyon kaçırıldı. Süreçte hangi iyileştirmeleri yaparsınız?",
            "Kapsam/öncelik çakışmalarında test planını nasıl oluşturursunuz?",
            "Kırılgan modül için otomasyon yaklaşımınız?",
        ],
    },
    {
        "key": "devops_engineer",
        "titles": ["devops", "site reliability", "platform engineer"],
        "competencies": ["CI/CD", "Infra as Code", "Monitoring", "Incident response"],
        "scenarios": [
            "Prod incident anında ilk 15 dakikada neleri yaparsınız?",
            "Kaynak maliyetleri arttı. Optimize planınız?",
            "Zero-downtime release için stratejiniz?",
        ],
    },
    {
        "key": "data_analyst",
        "titles": ["veri analisti", "data analyst"],
        "competencies": ["Modelleme", "SQL", "Görselleştirme", "İş sorusu çevirisi"],
        "scenarios": [
            "Eksik/çelişkili veride güvenilir KPI nasıl üretirsiniz?",
            "AB testinin anlamlılığını nasıl değerlendirirsiniz?",
            "İş birimi sorusunu analitik hipoteze çevirme örneği?",
        ],
    },
    {
        "key": "data_scientist",
        "titles": ["veri bilimci", "data scientist", "ml engineer"],
        "competencies": ["Feature engineering", "Model seçimi", "Validasyon", "Üretime alma"],
        "scenarios": [
            "Model drift tespit ettiniz. Ne yaparsınız?",
            "Performans ve açıklanabilirlik trade-off'unu nasıl yönetirsiniz?",
            "ML pipeline'ı üretime güvenle nasıl alırsınız?",
        ],
    },
    {
        "key": "product_manager",
        "titles": ["ürün yöneticisi", "product manager"],
        "competencies": ["Roadmap", "Önceliklendirme", "Kullanıcı görüşmesi", "KPI"],
        "scenarios": [
            "KPI düşüşünde problem alanını nasıl keşfedersiniz?",
            "Stakeholder çatışmalarında önceliklendirmeyi nasıl savunursunuz?",
            "Yanlış giden bir feature lansmanını nasıl kurtarırsınız?",
        ],
    },
    {
        "key": "project_manager",
        "titles": ["proje yöneticisi", "project manager", "scrum master"],
        "competencies": ["Planlama", "Risk", "Kaynak", "İletişim"],
        "scenarios": [
            "Kritik milestone gecikiyor. Kurtarma planınız?",
            "Scope creep'i nasıl yönetirsiniz?",
            "Çoklu paydaşlı projede şeffaf iletişimi nasıl sağlarsınız?",
        ],
    },
    {
        "key": "digital_marketing",
        "titles": ["dijital pazarlama", "performance marketing", "growth"],
        "competencies": ["Kanal stratejisi", "Bütçe", "Attribution", "Deney"],
        "scenarios": [
            "CPA yükseldi. Hangi hipotezleri test eder ve nasıl optimize edersiniz?",
            "Yeni kanalı düşük bütçeyle nasıl doğrularsınız?",
            "Attribution değişikliğinde raporlama farklarını nasıl açıklarsınız?",
        ],
    },
    {
        "key": "social_media",
        "titles": ["sosyal medya uzmanı", "social media", "community"],
        "competencies": ["İçerik", "Topluluk", "Kriz", "Analitik"],
        "scenarios": [
            "Negatif viral yorumlar var. Krizi nasıl yönetirsiniz?",
            "Organik erişimi nasıl artırırsınız?",
            "Influencer işbirliğinin başarısını nasıl ölçersiniz?",
        ],
    },
    {
        "key": "warehouse_supervisor",
        "titles": ["depo sorumlusu", "warehouse supervisor"],
        "competencies": ["Stok yönetimi", "Sayım", "İş güvenliği", "Verimlilik"],
        "scenarios": [
            "Sayım farklarını nasıl kalıcı azaltırsınız?",
            "Yerleşim ve toplama hızını nasıl iyileştirirsiniz?",
            "İş güvenliği ihlallerini azaltmak için planınız?",
        ],
    },
    {
        "key": "graphic_designer",
        "titles": ["grafik tasarımcı", "graphic designer"],
        "competencies": ["Brief çevirisi", "Revizyon yönetimi", "Deadline", "Kalite"],
        "scenarios": [
            "Belirsiz brief ile gelen işte netleştirme adımlarınız?",
            "Son dakika revizyonlarında kaliteyi nasıl korursunuz?",
            "Marka tutarlılığını ekip genelinde nasıl sağlarsınız?",
        ],
    },
    {
        "key": "sales_engineer",
        "titles": ["satış mühendisi", "sales engineer", "bölge satış mühendisi"],
        "competencies": ["B2B satış", "Teknik sunum", "Saha ziyaret", "Teklif yönetimi"],
        "scenarios": [
            "Teknik şartnamede gereksinimler değişti. Teklifi nasıl revize eder ve müşteriyi nasıl ikna edersiniz?",
            "Rakip daha düşük fiyat verdi. Değer odaklı satışla nasıl sonuç alırsınız?",
            "Saha denemesinde ürün beklenen performansı göstermedi. Krizi nasıl yönetirsiniz?",
        ],
    },
    {
        "key": "area_sales_manager",
        "titles": ["bölge satış müdürü", "area sales manager"],
        "competencies": ["Hedef yönetimi", "Saha ekibi yönetimi", "Pipeline", "Raporlama"],
        "scenarios": [
            "Bölge hedefleri geride. 30-60-90 günlük toparlama planınız nedir?",
            "Dağıtım kanalında çatışma var. Nasıl hizalar ve motivasyonu artırırsınız?",
            "Bölge potansiyelini artırmak için sahada neyi değiştirirsiniz?",
        ],
    },
    {
        "key": "field_sales_rep",
        "titles": ["saha satış temsilcisi", "field sales", "saha satış"],
        "competencies": ["Saha rut planı", "İtiraz yönetimi", "Tanzim-teşhir", "Tahsilat"],
        "scenarios": [
            "Zor bayiyle fiyat/iskonto tartışması. Nasıl yönetirsiniz?",
            "Rutin dışı acil ziyaret ihtiyacı doğdu. Planı nasıl yeniden kurgularsınız?",
            "Tahsilat gecikiyor. İlişkiyi bozmadan nasıl çözer ve kayda alırsınız?",
        ],
    },
    {
        "key": "production_operator",
        "titles": ["üretim operatörü", "üretim işçisi", "operatör"],
        "competencies": ["İş güvenliği", "Kalite bilinci", "Standart iş", "5S"],
        "scenarios": [
            "Hattın OEE değeri düştü. Kendi istasyonunuzda neleri iyileştirirsiniz?",
            "İş güvenliği ihlali riski fark ettiniz. Nasıl raporlar ve önlersiniz?",
            "İlk ürün onayında red aldınız. Kök neden ve aksiyonlarınız?",
        ],
    },
    {
        "key": "production_engineer",
        "titles": ["üretim mühendisi"],
        "competencies": ["Hat dengeleme", "Verimlilik", "Süreç iyileştirme", "Yalın araçlar"],
        "scenarios": [
            "Darboğaz istasyon tespit ettiniz. Hangi metotla çözersiniz?",
            "Yeni model devreye alınacak. PPAP/ilk ürün sürecini nasıl yönetirsiniz?",
            "Hurda oranı yükseldi. Analiz ve iyileştirme yaklaşımınız?",
        ],
    },
    {
        "key": "maintenance_technician",
        "titles": ["bakım teknisyeni", "bakım onarım teknikeri"],
        "competencies": ["Arıza analizi", "Planlı bakım", "Kestirimci bakım", "Yedek parça"],
        "scenarios": [
            "Kritik ekipman arızası üretimi durdurdu. İlk 30 dakikada ne yaparsınız?",
            "Kestirimci bakım verileri anomali gösteriyor. Nasıl yorumlar ve planlarsınız?",
            "Yedek parça tedarik gecikiyor. Geçici çözümünüz nedir?",
        ],
    },
    {
        "key": "quality_assurance_specialist",
        "titles": ["kalite güvence uzmanı"],
        "competencies": ["Dokümantasyon", "İç denetim", "8D/5Why", "Müşteri şikayeti"],
        "scenarios": [
            "Müşteri şikayeti aldınız. Kök neden analizi ve aksiyon planınızı anlatın.",
            "ISO denetiminde major uygunsuzluk çıktı. Hızlı düzeltici faaliyet planınız?",
            "Değişiklik yönetimi sırasında kalite riskini nasıl kontrol edersiniz?",
        ],
    },
    {
        "key": "quality_control_engineer",
        "titles": ["kalite kontrol mühendisi"],
        "competencies": ["Ölçüm teknikleri", "Kontrol planı", "Numune alma", "İstatistiksel süreç kontrol"],
        "scenarios": [
            "SPC grafikleri limit dışını gösteriyor. Nasıl müdahale edersiniz?",
            "Giriş kalite kabul oranı düştü. Tedarikçi geri bildiriminiz nedir?",
            "Kontrol planını nasıl güncellersiniz?",
        ],
    },
    {
        "key": "warehouse_worker",
        "titles": ["depo elemanı", "depo personeli"],
        "competencies": ["Adresleme", "Toplama", "Sevkiyat", "Güvenlik"],
        "scenarios": [
            "Yoğun gün sonu sevkiyatında hata oranını nasıl düşürürsünüz?",
            "Adresleme karıştı. Hızlı düzeltme planınız nedir?",
            "Hasarlı ürün tespiti halinde izlediğiniz süreç nedir?",
        ],
    },
    {
        "key": "warehouse_manager",
        "titles": ["depo müdürü", "depo sorumlusu"],
        "competencies": ["Kapasite planlama", "Stok doğruluğu", "Ekip yönetimi", "Maliyet"],
        "scenarios": [
            "Sayım farklarını azaltmak için hangi sistematikleri kurarsınız?",
            "Pik sezonda vardiya ve layout planınız nasıl olur?",
            "Lojistik maliyet baskısını nasıl yönetirsiniz?",
        ],
    },
    {
        "key": "logistics_planner",
        "titles": ["lojistik planlama uzmanı", "lojistik planlama"],
        "competencies": ["Rota", "Yükleme planı", "SLA", "Maliyet"],
        "scenarios": [
            "Gün içi acil sevkiyat talebi geldi. Planı nasıl revize edersiniz?",
            "Taşıma maliyetleri arttı. Optimizasyon hipotezleriniz?",
            "SLA ihlali trend gösteriyor. Hangi KPI'larla yönetirsiniz?",
        ],
    },
    {
        "key": "purchasing_manager",
        "titles": ["satınalma müdürü", "satın alma müdürü"],
        "competencies": ["Kategori yönetimi", "Sözleşme", "Maliyet", "Risk"],
        "scenarios": [
            "Tek kaynaktan tedarik riskli. Alternatif ve geçiş stratejiniz?",
            "Kur dalgalanmasında fiyat sabitlemeyi nasıl sağlarsınız?",
            "Tedarikçi performansını nasıl izler ve iyileştirirsiniz?",
        ],
    },
    {
        "key": "hr_manager",
        "titles": ["ik müdürü", "insan kaynakları müdürü"],
        "competencies": ["İşe alım stratejisi", "Performans", "Çalışan deneyimi", "Uyum"],
        "scenarios": [
            "Yüksek turnover sorununu nasıl analiz eder ve azaltırsınız?",
            "Performans sistemine güven düşük. Güven tesis planınız?",
            "Hızlı büyümede işe alım kalitesini nasıl korursunuz?",
        ],
    },
    {
        "key": "payroll_specialist",
        "titles": ["bordro uzmanı", "özlük işleri uzmanı"],
        "competencies": ["Bordro", "SGK", "Yan haklar", "Mevzuat"],
        "scenarios": [
            "Acil toplu bordro düzeltme ihtiyacı doğdu. Hangi kontrolleri yaparsınız?",
            "Eksik bildirimin tespiti sonrası süreç?",
            "Yan haklarda değişiklikleri çalışan iletişimiyle nasıl yönetirsiniz?",
        ],
    },
    {
        "key": "accounting_manager",
        "titles": ["muhasebe müdürü"],
        "competencies": ["Kapanış", "Vergi", "Denetim", "Ekip yönetimi"],
        "scenarios": [
            "Ay sonu kapanışta gecikme. Süreç iyileştirme planınız?",
            "Vergi incelemesinde talep edilen evraklarda sorun. Nasıl yönetirsiniz?",
            "Ekipte iş dağılımı dengesiz. Yeniden tasarım yaklaşımınız?",
        ],
    },
    {
        "key": "ar_ap_specialist",
        "titles": ["alacak takip uzmanı", "cari hesap uzmanı", "ar/ap uzmanı"],
        "competencies": ["Cari mutabakat", "Tahsilat", "Fatura", "Raporlama"],
        "scenarios": [
            "Geciken alacaklar artıyor. Risk ve aksiyon planınız?",
            "Cari mutabakatta uyuşmazlık. Nasıl çözümlersiniz?",
            "Hızlı ölçeklenmede süreçleri nasıl standardize edersiniz?",
        ],
    },
    {
        "key": "financial_analyst",
        "titles": ["finansal analist", "financial analyst"],
        "competencies": ["Bütçe", "Modelleme", "Raporlama", "KPI"],
        "scenarios": [
            "Bütçe sapmasını kök nedenleriyle nasıl ayrıştırırsınız?",
            "Yeni yatırımın geri dönüş analizini nasıl yaparsınız?",
            "Likidite stres testi nasıl tasarlanır?",
        ],
    },
    {
        "key": "electrician",
        "titles": ["elektrikçi"],
        "competencies": ["Arıza", "Kurulum", "Güvenlik", "Dokümantasyon"],
        "scenarios": [
            "Şantiye enerji kesintisi. Hızlı çözüm planınız?",
            "Pano montajında uygunsuzluk tespiti. Nasıl düzeltirsiniz?",
            "Periyodik bakımda önceliklendirme yaklaşımınız?",
        ],
    },
    {
        "key": "electronics_technician",
        "titles": ["elektronik teknisyeni"],
        "competencies": ["Kart tamiri", "Test", "Kalibrasyon", "Ekipman"],
        "scenarios": [
            "Arızalı kartın bileşen seviyesinde onarımı nasıl yaparsınız?",
            "Test jig'inde tutarsız sonuçlar. Nasıl doğrularsınız?",
            "Kalibrasyon dışı ekipmanı nasıl ele alırsınız?",
        ],
    },
    {
        "key": "mechanical_engineer",
        "titles": ["makine mühendisi"],
        "competencies": ["Tasarım/üretim", "Bakım", "Proje", "Maliyet"],
        "scenarios": [
            "Yeni makine yatırımında teknik/finansal değerlendirme yapın.",
            "Titreşim kaynaklı arıza tekrar ediyor. Kök neden ve çözüm?",
            "Enerji verimliliği iyileştirmesi için yaklaşımınız?",
        ],
    },
    {
        "key": "industrial_engineer",
        "titles": ["endüstri mühendisi"],
        "competencies": ["Süreç analizi", "Verimlilik", "Yalın", "Kapasite"],
        "scenarios": [
            "Sipariş artışında kapasite yetmiyor. Hat dengeleme planınız?",
            "Operasyonlarda israf tespiti ve A3 iyileştirme örneğiniz?",
            "Rota/iş yükü planlamasını nasıl optimize edersiniz?",
        ],
    },
    {
        "key": "civil_engineer",
        "titles": ["inşaat mühendisi", "şantiye şefi"],
        "competencies": ["Şantiye yönetimi", "Keşif/metraj", "Kalite/Güvenlik", "Planlama"],
        "scenarios": [
            "Kritik beton dökümünde kalite riski. Nasıl yönetirsiniz?",
            "Metraj farkı çıktı. Süreci nasıl düzeltirsiniz?",
            "Alt yüklenici gecikmeleri ile mücadele planınız?",
        ],
    },
    {
        "key": "nurse",
        "titles": ["hemşire"],
        "competencies": ["Hasta bakımı", "İletişim", "Hijyen", "Acil durum"],
        "scenarios": [
            "Yoğun serviste önceliklendirmeyi nasıl yaparsınız?",
            "Zor hasta yakını iletişimini nasıl yönetirsiniz?",
            "İlaç güvenliği hatası riskini nasıl azaltırsınız?",
        ],
    },
    {
        "key": "administrative_assistant",
        "titles": ["idari işler asistanı", "ofis asistanı", "sekreter"],
        "competencies": ["Takvim", "Evrak", "İletişim", "Koordinasyon"],
        "scenarios": [
            "Çakışan toplantı taleplerinde nasıl önceliklendirirsiniz?",
            "Acil evrak/kurye sorununda çözüm adımlarınız?",
            "Ziyaretçi yönetimini nasıl standardize edersiniz?",
        ],
    },
    {
        "key": "receptionist",
        "titles": ["resepsiyonist"],
        "competencies": ["Karşılama", "Telefon", "Kayıt", "Koordinasyon"],
        "scenarios": [
            "Yoğun saatlerde beklemeyi nasıl azaltırsınız?",
            "Şikayetçi ziyaretçiyi nasıl yatıştırır ve yönlendirirsiniz?",
            "Gizlilik içeren bir misafir kaydını nasıl yönetirsiniz?",
        ],
    },
    {
        "key": "hotel_front_office",
        "titles": ["ön büro görevlisi"],
        "competencies": ["Check-in/out", "Rezervasyon", "Müşteri memnuniyeti", "Şikayet"],
        "scenarios": [
            "Overbooking yaşandı. Çözüm ve iletişim planınız?",
            "VIP konuk özel isteği. Nasıl koordine edersiniz?",
            "Negatif yorum sonrası telafi süreciniz?",
        ],
    },
    {
        "key": "waiter",
        "titles": ["garson", "servis elemanı"],
        "competencies": ["Servis", "Hijyen", "İletişim", "Ekip"],
        "scenarios": [
            "Yoğun servis esnasında sipariş karışıklığını nasıl çözersiniz?",
            "Gıda alerjisi olan müşteri için prosedürünüz nedir?",
            "Şikayet yönetimini nasıl yaparsınız?",
        ],
    },
    {
        "key": "chef",
        "titles": ["aşçı", "şef"],
        "competencies": ["Mise en place", "Gıda güvenliği", "Maliyet", "Ekip"],
        "scenarios": [
            "Aniden artan siparişte kaliteyi nasıl korursunuz?",
            "Gıda maliyetleri yükseldi. Menü ve porsiyon yönetiminiz?",
            "Hijyen denetiminde çıkan uygunsuzlukları nasıl düzeltirsiniz?",
        ],
    },
    {
        "key": "textile_pattern_maker",
        "titles": ["modelist", "kalıpçı", "pattern maker"],
        "competencies": ["Kalıp", "Prova", "Serileme", "İş birliği"],
        "scenarios": [
            "Zor kalıp geçişinde tolerans sorunlarını nasıl çözersiniz?",
            "Prova geri bildirimlerini seriye nasıl uygularsınız?",
            "Numune yetişmiyor. Alternatif planınız nedir?",
        ],
    },
    {
        "key": "textile_quality_specialist",
        "titles": ["tekstil kalite kontrol", "kalite kontrol elemanı (tekstil)"],
        "competencies": ["Numune", "Sevkiyat öncesi kontrol", "AQL", "Raporlama"],
        "scenarios": [
            "Sevkiyat öncesi kontrolde uygunsuzluk. Müşteri iletişimi ve aksiyonlarınız?",
            "AQL kabul oranı düştü. Süreçte neyi değiştirirsiniz?",
            "Tedarikçi kalite takibini nasıl yaparsınız?",
        ],
    },
    {
        "key": "store_cashier",
        "titles": ["kasiyer"],
        "competencies": ["Kasa", "EFT/pos", "İade/Değişim", "Müşteri iletişimi"],
        "scenarios": [
            "Kasa açık/fazla durumunda izlenecek adımlarınız?",
            "Yoğun saatlerde sıra yönetimi nasıl olmalı?",
            "İade prosedüründe müşteriyle anlaşmazlık. Nasıl çözerirsiniz?",
        ],
    },
    {
        "key": "visual_merchandiser",
        "titles": ["görsel düzenleme uzmanı", "visual merchandiser"],
        "competencies": ["Vitrin", "Planogram", "Dönüşüm oranı", "Koordinasyon"],
        "scenarios": [
            "Yeni kampanya vitrinini nasıl planlar ve ölçersiniz?",
            "Merkez yönergesi ile mağaza kısıtları çakışıyor. Çözümünüz?",
            "Dönüşüm oranını artırmak için hangi değişiklikleri yaparsınız?",
        ],
    },
    {
        "key": "call_center_collections",
        "titles": ["tahsilat uzmanı (call center)", "tahsilat uzmanı"],
        "competencies": ["İtiraz yönetimi", "Tahsilat", "Hukuk süreçleri", "Script"],
        "scenarios": [
            "Zor müşteride tahsilatı nasıl başarırsınız?",
            "Hukuk öncesi uyarı süreçlerini nasıl yönetirsiniz?",
            "Script dışı durumlarda nasıl esnersiniz?",
        ],
    },
    {
        "key": "field_auditor",
        "titles": ["saha denetim uzmanı", "saha denetçi"],
        "competencies": ["Denetim", "Raporlama", "Uyum", "İletişim"],
        "scenarios": [
            "Sahada uygunsuzluk tespit ettiniz. Düzeltici faaliyet planınız?",
            "Şüpheli işlemde kanıt toplama ve raporlama yaklaşımınız?",
            "Denetim sonuçlarını saha ekibiyle nasıl paylaşırsınız?",
        ],
    },
    {
        "key": "security_guard",
        "titles": ["güvenlik görevlisi"],
        "competencies": ["Giriş-çıkış", "Acil durum", "Rapor", "Devriye"],
        "scenarios": [
            "Acil tahliye gerektiren bir olayda ilk adımlarınız?",
            "Ziyaretçi prosedürü ihlalinde nasıl müdahale edersiniz?",
            "Kamera tespitinde şüpheli davranış. Süreciniz nedir?",
        ],
    },
    {
        "key": "cleaning_staff",
        "titles": ["temizlik görevlisi"],
        "competencies": ["Hijyen", "Plan", "Kimyasal güvenlik", "İletişim"],
        "scenarios": [
            "Yoğun etkinlik sonrası alanı hızla nasıl toparlarsınız?",
            "Hijyen denetiminde çıkan eksikleri nasıl kapatırsınız?",
            "Kimyasal kullanımıyla ilgili güvenliği nasıl sağlarsınız?",
        ],
    },
]


from typing import Any, Dict, List, Optional


def select_role_context(job_text: str) -> Optional[Dict[str, Any]]:
    """Pick best matching role config from job text.

    Simple lowercase substring match over provided titles.
    """
    if not job_text:
        return None
    low = job_text.lower()
    best: Optional[Dict[str, Any]] = None
    for role in ROLE_PROMPTS:
        raw_titles = role.get("titles")
        titles = [str(t).lower() for t in raw_titles] if isinstance(raw_titles, list) else []
        if any(t in low for t in titles):
            best = role  # first match wins; list ordered by frequency
            break
    return best


def build_role_guidance_block(job_text: str) -> str:
    cfg = select_role_context(job_text)
    if not cfg:
        return ""
    comps = [str(x) for x in (cfg.get("competencies") or [])]
    scens = [str(x) for x in (cfg.get("scenarios") or [])]
    titles_raw = cfg.get("titles")
    titles = [str(x) for x in titles_raw] if isinstance(titles_raw, list) else []
    comp = ", ".join(comps)
    scns = "\n- ".join(scens)
    title = titles[0] if titles else str(cfg.get("key", ""))
    return (
        f"ROL: {title}\n"
        f"HEDEF YETKİNLİKLER: {comp}\n"
        f"ROL-ÖZEL DURUM SORULARI ÖRNEKLERİ:\n- {scns}"
    )


