import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import { Button } from "@/components/ui/Button";
import { Steps } from "@/components/ui/Steps";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      <MarketingNav active="home" />

      {/* Hero Section */}
      <section className="px-6 py-20 text-center bg-gradient-to-b from-brand-25 to-white dark:from-neutral-900 dark:to-neutral-950 animate-in fade-in-0 slide-in-from-top-2 duration-700">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6 flex justify-center">
            <img src="/logo.png" alt="Logo" className="h-10 w-10 rounded-xl ring-1 ring-brand-200/60" />
          </div>
          <div className="inline-flex items-center px-3 py-1 mb-6 text-sm text-brand-700 bg-brand-100 dark:text-brand-300 dark:bg-brand-700/20 rounded-full">
            <span className="mr-2">🆕</span>
            Kuruluş içinde ekipler oluşturun
          </div>
          <h1 className="mb-6 text-5xl font-bold text-gray-900 dark:text-neutral-100 leading-tight">
            İşe alım sürecinizi yapay zekâ ile hızlandırın
          </h1>
          <p className="mb-8 text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            RecruiterAI, çok sayıda işletme, kurum ve işe alım uzmanı tarafından ön eleme ve işe alım süreçlerini önemli ölçüde iyileştirmek için kullanılmaktadır.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <a href="/contact?utm_source=site&utm_medium=cta&utm_campaign=hero" className="inline-block">
              <Button size="lg">Demo Talep Et</Button>
            </a>
            <a href="/how-it-works?utm_source=site&utm_medium=cta&utm_campaign=hero_more" className="inline-block">
              <Button size="lg" variant="outline">Daha fazla bilgi</Button>
            </a>
          </div>
          {/* Güven unsurları kaldırıldı */}
        </div>
      </section>

      {/* Gerçek Hayat Senaryoları */}
      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-neutral-100 text-center mb-10">Gerçek Hayat Senaryoları</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="p-6 border rounded-lg bg-white dark:bg-neutral-900 dark:border-neutral-800">
              <div className="text-3xl mb-2">📈</div>
              <h3 className="text-lg font-semibold mb-2">Yoğun başvuru dönemleri</h3>
              <p className="text-gray-600 dark:text-gray-300 mb-3">İlanınız bir günde yüzlerce başvuru alıyor. RecruiterAI aday yanıtlarını özetleyip skorluyor; İK ilk 20 adaya dakikalar içinde odaklanıyor.</p>
              <a href="/contact?utm_source=site&utm_medium=cta&utm_campaign=scenario_high_volume" className="text-brand-700 font-semibold">Demo ile deneyin →</a>
            </div>
            <div className="p-6 border rounded-lg bg-white dark:bg-neutral-900 dark:border-neutral-800">
              <div className="text-3xl mb-2">🧑‍💻</div>
              <h3 className="text-lg font-semibold mb-2">Dağıtık ekiplerde değerlendirme</h3>
              <p className="text-gray-600 dark:text-gray-300 mb-3">Ekip üyeleri farklı şehirlerde. Ortak rapor ve kısa özetler karar toplantısını hızlandırıyor, herkes aynı veriye bakıyor.</p>
              <a href="/how-it-works?utm_source=site&utm_medium=cta&utm_campaign=scenario_remote" className="text-brand-700 font-semibold">Nasıl çalıştığını görün →</a>
            </div>
            <div className="p-6 border rounded-lg bg-white dark:bg-neutral-900 dark:border-neutral-800">
              <div className="text-3xl mb-2">⚖️</div>
              <h3 className="text-lg font-semibold mb-2">Önyargıyı azaltma</h3>
              <p className="text-gray-600 dark:text-gray-300 mb-3">Standart soru setleri ve rubric ile adaylar tutarlı kriterlerle değerlendiriliyor; subjektif yorumların etkisi azalıyor.</p>
              <a href="/solutions?utm_source=site&utm_medium=cta&utm_campaign=scenario_bias" className="text-brand-700 font-semibold">Çözümleri inceleyin →</a>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-6 py-16 bg-gray-50 dark:bg-neutral-900 animate-in fade-in-0 slide-in-from-bottom-2 duration-700">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-brand-700 dark:text-brand-300 font-semibold mb-4">NASIL ÇALIŞIR</p>
          <h2 className="text-4xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
            Üç basit adımda kolay kurulum
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-12 max-w-2xl mx-auto">
            Kullanımı kolay yapay zekâ aracı ve büyüme analitiği; dönüşüm, etkileşim ve elde tutmayı artırmak için tasarlanmıştır.
          </p>
          <Steps
            current={0}
            steps={["İlan oluştur", "Adayları davet et", "AI analizini incele"]}
            className="justify-center"
          />
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-16 animate-in fade-in-0 zoom-in-95 duration-700">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-8 border border-gray-200 dark:border-neutral-800 rounded-lg hover:shadow-lg transition-shadow bg-white dark:bg-neutral-900">
              <p className="text-brand-700 dark:text-brand-300 font-semibold mb-2">ÖZELLİK</p>
              <h3 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                Otomatik Aday Sıralama
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                Yapay zekâ, adayları nitelik, deneyim ve becerilere göre analiz edip sıralar; böylece en umut verici adaylara odaklanırsınız.
              </p>
              <button className="text-brand-700 font-semibold hover:text-brand-600">
                Demo talep et →
              </button>
            </div>
            
            <div className="p-8 border border-gray-200 dark:border-neutral-800 rounded-lg hover:shadow-lg transition-shadow bg-white dark:bg-neutral-900">
              <p className="text-brand-700 dark:text-brand-300 font-semibold mb-2">ÖZELLİK</p>
              <h3 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                Gerçek Zamanlı Aday Analitiği
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                Aday performansı ve mülakat metrikleri hakkında kapsamlı içgörüler elde ederek veriye dayalı işe alım kararları verin.
              </p>
              <button className="text-brand-700 font-semibold hover:text-brand-600">
                Demo talep et →
              </button>
            </div>
            
            <div className="p-8 border border-gray-200 dark:border-neutral-800 rounded-lg hover:shadow-lg transition-shadow bg-white dark:bg-neutral-900">
              <p className="text-brand-700 dark:text-brand-300 font-semibold mb-2">ÖZELLİK</p>
              <h3 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                Kesintisiz Çok Dilli Destek
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                Yapay zekâ destekli çeviri ve analiz yetenekleriyle birden fazla dilde mülakatlar gerçekleştirin.
              </p>
              <button className="text-brand-700 font-semibold hover:text-brand-600">
                Demo talep et →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Neden RecruiterAI? */}
      <section className="px-6 py-16 bg-gray-50 dark:bg-neutral-900">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-neutral-100 text-center mb-10">Neden RecruiterAI?</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="p-6 border rounded-lg bg-white dark:bg-neutral-900 dark:border-neutral-800">
              <h3 className="text-lg font-semibold mb-2">Türkçe Yapay Zekâ</h3>
              <p className="text-gray-600 dark:text-gray-300">TR pazarına uygun dil anlama, transkript ve rapor üretimi. KVKK odaklı mimari.</p>
            </div>
            <div className="p-6 border rounded-lg bg-white dark:bg-neutral-900 dark:border-neutral-800">
              <h3 className="text-lg font-semibold mb-2">Dakikalar İçinde Kurulum</h3>
              <p className="text-gray-600 dark:text-gray-300">Ekstra yazılım kurmadan, tarayıcı üzerinden hızlı devreye alma ve davet.</p>
            </div>
            <div className="p-6 border rounded-lg bg-white dark:bg-neutral-900 dark:border-neutral-800">
              <h3 className="text-lg font-semibold mb-2">Şeffaf Skor & Rapor</h3>
              <p className="text-gray-600 dark:text-gray-300">İletişim, teknik ve kültürel uyum skorları; özet yorumlar ve paylaşılabilir rapor.</p>
            </div>
          </div>
          <div className="text-center mt-8">
            <a href="/contact?utm_source=site&utm_medium=cta&utm_campaign=why_recruiterai" className="inline-block">
              <Button size="lg">Demo Talep Et</Button>
            </a>
          </div>
        </div>
      </section>

      {/* SSS */}
      <section className="px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-neutral-100 text-center mb-10">Sıkça Sorulan Sorular</h2>
          <div className="space-y-4">
            {[
              { q: "Kurulum için teknik ekip gerekiyor mu?", a: "Hayır. Tarayıcı üzerinden çalışır; davet linkiyle adayı içeri alırsınız." },
              { q: "Perakende dönemsel yoğunlukta ilk görüşmeleri nasıl yetiştirirsiniz?", a: "Standart soru seti ile kısa video yanıtları toplanır, özetlenir ve sıralanır; ekip yalnızca uygun adaylara odaklanır." },
              { q: "Çağrı merkezinde tutarlılığı nasıl korursunuz?", a: "İletişim/empati gibi yetkinlikler aynı rubric ile puanlanır; değerlendiriciler arası fark azalır." },
            ].map((item, idx) => (
              <details key={idx} className="group border border-neutral-200 dark:border-neutral-800 rounded-lg p-4">
                <summary className="flex cursor-pointer list-none items-center justify-between">
                  <span className="font-semibold">{item.q}</span>
                  <span className="transition-transform group-open:rotate-45">＋</span>
                </summary>
                <p className="mt-2 text-gray-700 dark:text-gray-300">{item.a}</p>
              </details>
            ))}
            <div className="text-center pt-2">
              <a className="text-brand-700 font-semibold" href="/faq">Tüm SSS’leri gör →</a>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials kaldırıldı */}

      <MarketingFooter />
    </div>
  );
} 