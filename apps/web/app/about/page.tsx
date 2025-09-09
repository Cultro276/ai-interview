import { companyName, productName } from "@/lib/brand";
import Image from "next/image";
import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-xl bg-gradient-to-br from-brand-50 to-white dark:from-neutral-900 dark:to-neutral-950 p-8 md:p-12 mb-8 border border-neutral-200 dark:border-neutral-800">
        <div className="flex items-center gap-4 mb-4">
          <div className="h-12 w-12 rounded-xl bg-white/80 dark:bg-neutral-800 flex items-center justify-center border border-neutral-200 dark:border-neutral-700 ring-1 ring-brand-200/60">
            <Image src="/logo.png" alt="Logo" width={28} height={28} />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-neutral-100">{companyName}</h1>
            <p className="text-gray-600 dark:text-gray-300">Türkiye’de etik ve fayda odaklı yapay zekâ ürünleri</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          <a href="#hikaye" className="px-4 py-2 rounded-lg border border-brand-700 text-brand-700 hover:bg-brand-25">Hikayemizi Oku</a>
          <Link href="/contact?utm_source=site&utm_medium=cta&utm_campaign=about_hero" className="px-4 py-2 rounded-lg bg-brand-700 text-white hover:bg-brand-600">İletişime Geç</Link>
        </div>
      </section>

      {/* Body with sticky TOC */}
      <div className="grid md:grid-cols-4 gap-6">
        <aside className="hidden md:block md:col-span-1">
          <div className="sticky top-24 space-y-2 p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
            <a href="#vizyon" className="block text-sm text-gray-700 dark:text-gray-300 hover:text-brand-700">Vizyon</a>
            <a href="#misyon" className="block text-sm text-gray-700 dark:text-gray-300 hover:text-brand-700">Misyon</a>
            <a href="#hikaye" className="block text-sm text-gray-700 dark:text-gray-300 hover:text-brand-700">Hikayemiz</a>
            <a href="#degerler" className="block text-sm text-gray-700 dark:text-gray-300 hover:text-brand-700">Değerler</a>
            <a href="#uyumluluk" className="block text-sm text-gray-700 dark:text-gray-300 hover:text-brand-700">KVKK</a>
          </div>
        </aside>

        <main className="md:col-span-3 space-y-10">
          <section className="">
            <h2 id="vizyon" className="text-2xl font-semibold mb-3">Vizyonumuz</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
                <div className="text-2xl mb-2">🌍</div>
                <p className="text-gray-700 dark:text-gray-300">
                  {companyName}, Türkiye’de işletmelerin süreçlerine güvenilir ve şeffaf yapay zekâyı entegre etmeyi yaygınlaştırmayı amaçlar. İlk ürünümüz {productName} olsa da vizyonumuz, İK’dan destek ve operasyonlara kadar farklı alanlarda etik ve fayda odaklı ürünler geliştirmek.
                </p>
              </div>
              <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
                <h3 className="font-semibold mb-1">Etki Alanı</h3>
                <p className="text-gray-700 dark:text-gray-300">İşe alımdan müşteri deneyimine uzanan süreçlerde ölçülebilir değer üreten, insanı merkeze alan ürünler.</p>
              </div>
            </div>
          </section>

          <section className="">
            <h2 id="misyon" className="text-2xl font-semibold mb-3">Misyonumuz</h2>
            <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
              <div className="text-2xl mb-2">🎯</div>
              <p className="text-gray-700 dark:text-gray-300">Türkçe dilinde yüksek doğrulukla çalışan, KVKK uyumlu ve iş sonuçlarına doğrudan etki eden yapay zekâ ürünleri geliştirmek. Ekiplerin tekrar eden işleri otomatikleştirip, karar anlarında şeffaf içgörüler sunarak verimliliği artırmak.</p>
            </div>
          </section>

          <section className="">
            <h2 id="hikaye" className="text-2xl font-semibold mb-3">Hikayemiz</h2>
            <ol className="relative border-l border-neutral-200 dark:border-neutral-800 ml-3">
              <li className="mb-6 ml-4">
                <div className="absolute -left-2 mt-1 h-3 w-3 rounded-full bg-brand-700"></div>
                <h3 className="font-semibold mb-1">İhtiyacı fark ettik</h3>
                <p className="text-gray-700 dark:text-gray-300">Büyüyen işe alım hacminde ekiplerin tutarlı ve hızlı karar vermekte zorlandığını gördük.</p>
              </li>
              <li className="mb-6 ml-4">
                <div className="absolute -left-2 mt-1 h-3 w-3 rounded-full bg-brand-700"></div>
                <h3 className="font-semibold mb-1">Çözümü tasarladık</h3>
                <p className="text-gray-700 dark:text-gray-300">Video yanıtları anlayan, rubric ile puanlayan ve özetleyen bir yardımcı geliştirdik.</p>
              </li>
              <li className="ml-4">
                <div className="absolute -left-2 mt-1 h-3 w-3 rounded-full bg-brand-700"></div>
                <h3 className="font-semibold mb-1">Yolculuk devam ediyor</h3>
                <p className="text-gray-700 dark:text-gray-300">{productName} bugün farklı ölçeklerde kullanılabilir; amacımız etik yapay zekâyı yaygınlaştırmak.</p>
              </li>
            </ol>
          </section>

          <section className="">
            <h2 id="degerler" className="text-2xl font-semibold mb-3">Değerler</h2>
            <div className="grid md:grid-cols-4 gap-4">
              <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900"><div className="text-2xl mb-2">🔍</div><h3 className="font-semibold mb-1">Şeffaflık</h3><p className="text-gray-700 dark:text-gray-300">Açıklanabilir skorlar, paylaşılabilir raporlar.</p></div>
              <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900"><div className="text-2xl mb-2">🔐</div><h3 className="font-semibold mb-1">Güvenlik</h3><p className="text-gray-700 dark:text-gray-300">Veri minimizasyonu ve erişim kontrolleri.</p></div>
              <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900"><div className="text-2xl mb-2">🤝</div><h3 className="font-semibold mb-1">İnsan Odaklı</h3><p className="text-gray-700 dark:text-gray-300">Karar verici insandır; AI destek olur.</p></div>
              <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900"><div className="text-2xl mb-2">⚡</div><h3 className="font-semibold mb-1">Hız</h3><p className="text-gray-700 dark:text-gray-300">Dakikalar içinde kurulum ve sonuç.</p></div>
            </div>
          </section>

          <section id="uyumluluk" className="">
            <div className="p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-gray-50 dark:bg-neutral-900">
              <p className="text-sm text-gray-700 dark:text-gray-300">KVKK odaklı mimari • Veri minimizasyonu • Denetim kayıtları • Şifreleme</p>
            </div>
          </section>

          <section className="">
            <div className="flex flex-wrap items-center justify-between gap-3 p-5 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
              <div>
                <h3 className="font-semibold mb-1">Sizin senaryonuz için konuşalım</h3>
                <p className="text-gray-700 dark:text-gray-300">Kısa bir demo ile {productName}&apos;i iş akışınıza göre gösterelim.</p>
              </div>
              <div className="flex gap-2">
                <Link href="/contact?utm_source=site&utm_medium=cta&utm_campaign=about_footer" className="px-4 py-2 rounded-lg bg-brand-700 text-white hover:bg-brand-600">Demo Talep Et</Link>
                <Link href="/how-it-works" className="px-4 py-2 rounded-lg border border-neutral-300 dark:border-neutral-700">Nasıl Çalışır?</Link>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}


