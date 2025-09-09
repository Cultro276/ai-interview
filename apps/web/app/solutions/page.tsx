import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import Image from "next/image";

export default function SolutionsPage() {
  return (
    <div className="min-h-screen bg-white">
      <MarketingNav active="home" />

      <section className="px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6 flex justify-center">
            <Image src="/logo.png" alt="Logo" width={40} height={40} className="h-10 w-10 rounded-xl ring-1 ring-brand-200/60" />
          </div>
          <h1 className="mb-6 text-5xl font-bold text-gray-900">Çözümler</h1>
          <p className="mb-12 text-xl text-gray-600 max-w-3xl mx-auto">
            RecruiterAI ile aday bulma, değerlendirme ve mülakat süreçlerinizi yapay zekâ ile hızlandırın. Eğitimden finans’a, perakendeden teknolojiye kadar farklı sektörlerde hızlı implementasyon.
          </p>
        </div>
      </section>

      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-8">
          <div className="p-8 border rounded-lg">
            <div className="text-3xl mb-2">🔎</div>
            <h3 className="text-xl font-bold mb-2">Aday Keşfi</h3>
            <p className="text-gray-600 mb-3">CV ve profillerden otomatik özet, yetkinlik çıkarımı ve önceliklendirme.</p>
            <a href="/contact?utm_source=site&utm_medium=cta&utm_campaign=solutions_discovery" className="text-brand-700 font-semibold">Demo talep et →</a>
          </div>
          <div className="p-8 border rounded-lg">
            <div className="text-3xl mb-2">🎥</div>
            <h3 className="text-xl font-bold mb-2">Video Mülakat</h3>
            <p className="text-gray-600 mb-3">Tarayıcıdan KVKK uyumlu kayıt, otomatik transkript ve soru akışı.</p>
            <a href="/how-it-works?utm_source=site&utm_medium=cta&utm_campaign=solutions_interview" className="text-brand-700 font-semibold">Nasıl çalışır? →</a>
          </div>
          <div className="p-8 border rounded-lg">
            <div className="text-3xl mb-2">📊</div>
            <h3 className="text-xl font-bold mb-2">Aday Skoru</h3>
            <p className="text-gray-600 mb-3">Teknik/iletişim/kültürel uyum metrikleri ile şeffaf skor ve rapor.</p>
            <a href="/solutions?utm_source=site&utm_medium=cta&utm_campaign=solutions_scoring" className="text-brand-700 font-semibold">Örnek rapor →</a>
          </div>
        </div>
      </section>

      <section className="px-6 py-16 bg-gray-50">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-2xl font-bold mb-3">Neden RecruiterAI?</h3>
            <ul className="list-disc list-inside text-gray-700 space-y-1">
              <li>Türkçe yapay zekâ ve KVKK odaklı mimari</li>
              <li>Kurulum gerektirmeyen hızlı devreye alma</li>
              <li>Ölçülebilir analiz ve raporlama</li>
              <li>Ekipler arası işbirliği ve paylaşımlar</li>
            </ul>
          </div>
          <div>
            <h3 className="text-2xl font-bold mb-3">Entegrasyonlar</h3>
            <p className="text-gray-700">ATS, SSO ve e‑posta entegrasyonlarıyla mevcut iş akışınıza kolay uyum.</p>
          </div>
        </div>
      </section>

      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <h3 className="text-2xl font-bold mb-6">Senaryo Bazlı Faydalar</h3>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="p-6 border rounded-lg">
              <h4 className="font-semibold mb-2">Yoğun başvuruda eleme hızlanır</h4>
              <p className="text-gray-700">Ön eleme için harcanan saatler, otomatik skor ve özetlerle dakikalara iner.</p>
            </div>
            <div className="p-6 border rounded-lg">
              <h4 className="font-semibold mb-2">Adil ve tutarlı değerlendirme</h4>
              <p className="text-gray-700">Standart rubric; pozisyonlar ve ekipler arası kıyaslamayı kolaylaştırır.</p>
            </div>
            <div className="p-6 border rounded-lg">
              <h4 className="font-semibold mb-2">Zaman ve maliyet tasarrufu</h4>
              <p className="text-gray-700">Ön görüşme yükünü azaltır; işe alım süresi ve maliyetleri düşer.</p>
            </div>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}


