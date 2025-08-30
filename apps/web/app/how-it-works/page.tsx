import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import { Steps } from "@/components/ui";

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen bg-white">
      <MarketingNav />

      <section className="px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6 flex justify-center">
            <img src="/logo.png" alt="Logo" className="h-10 w-10 rounded-xl ring-1 ring-brand-200/60" />
          </div>
          <h1 className="mb-6 text-5xl font-bold text-gray-900">Nasıl Çalışır</h1>
          <p className="mb-12 text-xl text-gray-600 max-w-3xl mx-auto">
            Üç basit adımda adaylarınızla video mülakata başlayın; yapay zekâ soruları yönetsin, transkript ve skorları otomatik üretin.
          </p>
          <div className="flex justify-center">
            <Steps current={0} steps={["İlan oluştur", "Adayları davet et", "Analizi paylaş"]} />
          </div>
        </div>
      </section>

      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-8">
          <div className="p-6 border rounded-lg">
            <h3 className="text-lg font-semibold">1) Kurulum</h3>
            <p className="text-gray-600">Dakikalar içinde ilanı açın, sorular otomatik hazırlansın.</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-lg font-semibold">2) Görüşme</h3>
            <p className="text-gray-600">Aday tarayıcıdan bağlanır; kayıt, transkript ve sinyaller toplanır.</p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-lg font-semibold">3) Skor & Rapor</h3>
            <p className="text-gray-600">İletişim, teknik, kültürel uyum skorları ve özet rapor hazır.</p>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}


