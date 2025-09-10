import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import { Button } from "@/components/ui";
import Image from "next/image";

export default function ContactPage() {
  const utm = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const utmFields = utm ? {
    source: utm.get('utm_source') || '',
    medium: utm.get('utm_medium') || '',
    campaign: utm.get('utm_campaign') || '',
    content: utm.get('utm_content') || '',
    term: utm.get('utm_term') || ''
  } : { source: '', medium: '', campaign: '', content: '', term: '' };
  return (
    <div className="min-h-screen bg-white">
      <MarketingNav active="contact" />

      {/* Hero Section */}
      <section className="px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6 flex justify-center">
            <Image src="/logo.png" alt="Logo" width={40} height={40} className="h-10 w-10 rounded-xl ring-1 ring-brand-200/60" />
          </div>
          <p className="text-blue-600 font-semibold mb-4">İLETİŞİM</p>
          <h1 className="mb-6 text-5xl font-bold text-gray-900">
            Yardımcı olmak için buradayız
          </h1>
          <p className="mb-12 text-xl text-gray-600 max-w-2xl mx-auto">
            Sorunuz, öneriniz mi var ya da yapay zekâ destekli işe alım çözümlerimiz hakkında daha fazla bilgi mi istiyorsunuz? Bize ulaşın!
          </p>
        </div>
      </section>

      {/* Help Options */}
      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Hızlıca destek alın</h2>
            <p className="text-gray-600 mb-4">
              İhtiyacınız olduğunda bize ulaşabilir veya belgelerimize göz atabilirsiniz.
            </p>
            <p className="text-gray-600">
              Yardım etmek ve sorularınızı yanıtlamak için buradayız. Sizden haber almayı sabırsızlıkla bekliyoruz!
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Documentation */}
            <div className="p-8 border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Belgeleri okuyun</h3>
              <p className="text-gray-600 mb-6">
                Yapay zekâ destekli işe alım çözümlerimiz ve şirketinize nasıl fayda sağlayabileceği hakkında ayrıntılı bilgi mi arıyorsunuz? 
                Kapsamlı belgelerimiz süreci adım adım anlatır ve sorularınızı yanıtlar.
              </p>
              <a href="/onboarding" className="inline-block">
                <Button variant="outline">Belgeleri görüntüle</Button>
              </a>
            </div>

            {/* Support Ticket */}
            <div className="p-8 border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Destek Talebi Oluşturun</h3>
              <p className="text-gray-600 mb-6">
                Hemen destek gerekiyorsa veya belirli bir sorunuz varsa, talep sistemimiz uzman ekibimize ulaşmanın en iyi yoludur. 
                Talep oluşturun; isteğinizi önceliklendirelim ve hızlıca yardımcı olalım.
              </p>
              <Button>Talep oluştur</Button>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Form */}
      <section className="px-6 py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Bize mesaj gönderin</h2>
            <p className="text-gray-600">
              Aşağıdaki formu doldurun; en kısa sürede size dönüş yapalım.
            </p>
          </div>

          <div className="bg-white p-8 rounded-lg shadow">
            <form className="space-y-6" action="https://formspree.io/f/mzbldemo" method="POST">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">Ad</label>
                  <input 
                    type="text" 
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                    placeholder="Adınızı girin"
                    name="first_name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">Soyad</label>
                  <input 
                    type="text" 
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                    placeholder="Soyadınızı girin"
                    name="last_name"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">E‑posta</label>
                <input 
                  type="email" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  placeholder="E‑posta adresinizi girin"
                name="email" />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">Şirket</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  placeholder="Şirket adınızı girin"
                name="company" />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">Mesaj</label>
                <textarea 
                  rows={5}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  placeholder="İhtiyaçlarınızdan bahsedin..."
                name="message"></textarea>
              </div>
              
              <Button className="w-full" type="submit">Mesajı Gönder</Button>
              {/* UTM Hidden Fields */}
              <input type="hidden" name="utm_source" value={utmFields.source} />
              <input type="hidden" name="utm_medium" value={utmFields.medium} />
              <input type="hidden" name="utm_campaign" value={utmFields.campaign} />
              <input type="hidden" name="utm_content" value={utmFields.content} />
              <input type="hidden" name="utm_term" value={utmFields.term} />
            </form>
          </div>
        </div>
      </section>

      {/* SSS kaldırıldı */}

      {/* CTA kaldırıldı */}

      <MarketingFooter />
    </div>
  );
} 