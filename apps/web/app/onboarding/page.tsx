import Image from "next/image";

export default function OnboardingPage() {
  return (
    <div className="max-w-5xl mx-auto p-6">
      <section className="rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-8 mb-8">
        <h1 className="text-3xl font-bold mb-2">Onboarding • Başlarken</h1>
        <p className="text-gray-700 dark:text-gray-300">RecruiterAI’ı ekibinizle 30 dakikada kullanıma açın. Aşağıdaki adımları izleyin.</p>
      </section>

      <div className="grid md:grid-cols-4 gap-6">
        <aside className="hidden md:block md:col-span-1">
          <div className="sticky top-24 space-y-2 p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 text-sm">
            <a href="#accounts" className="block">Hesap ve Üyeler</a>
            <a href="#job" className="block">İlan Oluşturma</a>
            <a href="#invite" className="block">Aday Daveti</a>
            <a href="#review" className="block">Analiz ve Rapor</a>
          </div>
        </aside>
        <main className="md:col-span-3 space-y-8">
          {/* Reusable lightweight placeholder */}
          {/* Not embedding binary screenshots; replace later with real images under /public/onboarding */}
          {(() => null)()}
          <section id="accounts" className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6">
            <h2 className="text-2xl font-semibold mb-3">1) Hesap ve Üyeler</h2>
            <div className="grid md:grid-cols-2 gap-4 items-start">
              <div>
                <ol className="list-decimal list-inside space-y-1 text-gray-700 dark:text-gray-300">
                  <li>Yönetim panelinden “Ekip” bölümünde “Üye Ekle” ile ekip arkadaşlarınızı davet edin.</li>
                  <li>Yetkileri (ilan/aday/mülakat/üye) ihtiyaca göre açın.</li>
                </ol>
              </div>
              <div className="rounded-md border border-neutral-200 dark:border-neutral-800 overflow-hidden">
                <Image src="/onboarding/accounts.png" alt="Üye ekleme ekranı" width={1200} height={700} />
              </div>
            </div>
          </section>
          <section id="job" className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6">
            <h2 className="text-2xl font-semibold mb-3">2) İlan Oluşturma</h2>
            <div className="grid md:grid-cols-2 gap-4 items-start">
              <p className="text-gray-700 dark:text-gray-300">Pozisyonu seçin, soru setini özelleştirin ve adaydan beklenen teslimleri tanımlayın.</p>
              <div className="rounded-md border border-neutral-200 dark:border-neutral-800 overflow-hidden">
                <Image src="/onboarding/job.png" alt="İlan oluşturma" width={1200} height={700} />
              </div>
            </div>
          </section>
          <section id="invite" className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6">
            <h2 className="text-2xl font-semibold mb-3">3) Aday Daveti</h2>
            <div className="grid md:grid-cols-2 gap-4 items-start">
              <div className="space-y-2 text-gray-700 dark:text-gray-300">
                <p>Toplu CV yüklediğinizde, sistem adayların e‑posta adreslerine mülakat linklerini otomatik gönderir.</p>
                <p>Tekil aday ekliyorsanız, adayın e‑posta adresini girmeniz yeterlidir; oluşturulduğunda link otomatik iletilir.</p>
                <p>SMS gönderimi yoktur.</p>
              </div>
              <div className="rounded-md border border-neutral-200 dark:border-neutral-800 overflow-hidden">
                <Image src="/onboarding/invite.png" alt="Aday daveti" width={1200} height={700} />
              </div>
            </div>
          </section>
          <section id="review" className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-6">
            <h2 className="text-2xl font-semibold mb-3">4) Analiz ve Rapor</h2>
            <div className="grid md:grid-cols-2 gap-4 items-start">
              <p className="text-gray-700 dark:text-gray-300">Skor, özet ve transkriptleri inceleyin; raporu ekip ile paylaşın veya PDF alın.</p>
              <div className="rounded-md border border-neutral-200 dark:border-neutral-800 overflow-hidden">
                <Image src="/onboarding/review.png" alt="Analiz ve rapor" width={1200} height={700} />
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}


