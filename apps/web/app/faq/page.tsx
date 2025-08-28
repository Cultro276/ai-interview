"use client";
import { useMemo, useState } from "react";

export default function FAQPage() {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"genel" | "guvenlik" | "entegrasyon" | "sektor">("genel");
  const faqs = [
    { q: "Kurulum için teknik ekip gerekiyor mu?", a: "Hayır. Tarayıcı üzerinden çalışır; davet linkiyle adayı içeri alırsınız." },
    { q: "Veriler nerede saklanıyor?", a: "KVKK odaklı olarak yetkili servis sağlayıcılarımızda saklanır; erişim politikaları uygulanır." },
    { q: "Raporlar nasıl paylaşılıyor?", a: "Panel üzerinden tek tıkla ekiple paylaşabilir, PDF’e aktarabilirsiniz." },
    { q: "Demo süreci nasıl işliyor?", a: "İletişim formundan talep bırakın; size özel senaryoyla kısa bir deneme açalım." },
    { q: "Yapay zekâ karar veriyor mu, yoksa destek mi oluyor?", a: "{\n}Yapay zekâ öneri ve skorlar üretir; nihai karar her zaman insan yöneticilerdedir. Standart rubric ile tutarlılığı artırır." },
    { q: "Veriler yapay zekâ modelini eğitmek için kullanılıyor mu?", a: "Hayır. Varsayılan olarak müşteri verileri model eğitimi için kullanılmaz. Hizmet kalitesini artırmak için anonimleştirilmiş metrikler kullanılabilir." },
    { q: "AI bazen hata yaparsa ne olur?", a: "Skor ve özetler yanında ham transkript ve videolara erişim sağlanır. Ekip dilerse manuel düzeltme/geri bildirim ekleyebilir." },
    { q: "Güvenlik standartlarınız neler?", a: "Veri şifreleme, erişim kontrolleri ve denetim kayıtları uygularız. Talep halinde veri saklama süresini kısaltabiliriz." },
    { q: "Farklı pozisyonlar için soru setlerini özelleştirebilir miyiz?", a: "Evet. Pozisyon bazlı soru şablonları ve değerlendirme kriterleri tanımlanabilir." },
    // Sektör bazlı – değerleri sezdiren sorular
    { q: "Perakendede yoğun aday akışında ilk görüşmeleri nasıl yetiştirirsiniz?", a: "Mağaza açılışları gibi dönemlerde başvurular artar. Standart soru setiyle adayların kısa video yanıtlarını toplayıp özetlersiniz; ekip yalnızca uygun olanlarla devam eder." },
    { q: "Çağrı merkezinde yüksek devir oranında tutarlılığı nasıl korursunuz?", a: "İletişim ve empati gibi yetkinlikleri aynı rubric’le puanladığınızda, farklı değerlendiriciler arasında tutarlılık doğal olarak yerleşir." },
    { q: "Teknolojide junior ve mid adayları ayırmak neden zor olur?", a: "Video yanıtlarındaki teknik açıklamalar anahtar kavramlara göre çıkarılır; temel ile uygulama farkı görünür hale gelir, ekip odağını doğru seviyeye taşır." },
    { q: "Lojistik/operasyonda vardiya bazlı işe alımı nasıl hızlandırırsınız?", a: "Adayların uygunluk ve düzen algısını kısa yanıtlarla ölçüp sıraladığınızda, sahadaki yöneticiye yalnızca planlanabilir adaylar iletilir." },
    { q: "Satış rollerinde kültürel uyumu nasıl önden anlarsınız?", a: "Senaryo sorularına verilen yaklaşımlar, ekip değerleriyle uyumu sezdirir; görüşmeye giden adayların hit oranı artar." },
  ];
  const groups = {
    genel: faqs.slice(0, 6),
    guvenlik: faqs.filter(f => f.q.includes("Güvenlik") || f.q.includes("Veriler") || f.q.includes("AI bazen hata")),
    entegrasyon: [{ q: "Farklı pozisyonlar için soru setlerini özelleştirebilir miyiz?", a: "Evet. Pozisyon bazlı şablonlar ve değerlendirme kriterleri tanımlanabilir." }],
    sektor: faqs.slice(-5),
  } as const;
  const items = useMemo(() => {
    const pool = groups[tab];
    if (!query.trim()) return pool;
    const q = query.toLowerCase();
    return pool.filter(i => i.q.toLowerCase().includes(q) || i.a.toLowerCase().includes(q));
  }, [query, tab]);
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-4 flex justify-center">
          <img src="/logo.png" alt="Logo" className="h-10 w-10 rounded-xl ring-1 ring-brand-200/60" />
        </div>
        <h1 className="text-3xl font-bold mb-4">Sıkça Sorulan Sorular</h1>
        <p className="text-gray-600 mb-4">Aradığını yaz ya da kategori seç.</p>
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ara..." className="px-3 py-2 border rounded-md" />
          <div className="flex gap-2 text-sm">
            {[
              { id: "genel", label: "Genel" },
              { id: "guvenlik", label: "Güvenlik/KVKK" },
              { id: "entegrasyon", label: "Entegrasyon" },
              { id: "sektor", label: "Sektörler" },
            ].map(t => (
              <button key={t.id} onClick={() => setTab(t.id as any)} className={`px-3 py-1 rounded-md border ${tab===t.id ? "bg-brand-700 text-white border-brand-700" : "border-neutral-300"}`}>{t.label}</button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {items.map((item, idx) => (
            <details key={idx} className="group border border-neutral-200 dark:border-neutral-800 rounded-lg p-4">
              <summary className="flex cursor-pointer list-none items-center justify-between">
                <span className="font-semibold">{item.q}</span>
                <span className="transition-transform group-open:rotate-45">＋</span>
              </summary>
              <p className="mt-2 text-gray-700 dark:text-gray-300">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}


