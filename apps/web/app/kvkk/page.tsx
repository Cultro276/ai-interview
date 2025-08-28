export default function KvkkPage() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 p-8">
        <h1 className="text-3xl font-bold mb-4">KVKK Aydınlatma Metni</h1>
        <p className="text-gray-700 dark:text-gray-300 mb-6">Bu sayfa, işe alım süreçlerinde işlenen kişisel verilerin korunması ve şeffaflık amacıyla hazırlanmıştır.</p>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">İşleme Amaçları</h2>
            <ul className="list-disc list-inside text-gray-700 dark:text-gray-300 space-y-1">
              <li>Mülakat planlama, yürütme ve değerlendirme</li>
              <li>Kalite, güvenlik ve denetim</li>
            </ul>
          </div>
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">Veri Kategorileri</h2>
            <ul className="list-disc list-inside text-gray-700 dark:text-gray-300 space-y-1">
              <li>Kimlik ve iletişim bilgileri</li>
              <li>Görüntü/ses kaydı, transkript</li>
              <li>Skorlar ve değerlendirme çıktıları</li>
            </ul>
          </div>
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">Hukuki Sebep</h2>
            <p className="text-gray-700 dark:text-gray-300">Açık rıza ve meşru menfaat; işe alım süreçlerinin yürütülmesi.</p>
          </div>
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">Aktarımlar</h2>
            <p className="text-gray-700 dark:text-gray-300">Yalnızca hizmet sağlayıcılarla ve yetkili kişilerle, veri minimizasyonu ile paylaşım yapılır.</p>
          </div>
        </div>

        <div className="mt-6 grid md:grid-cols-2 gap-6">
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">Saklama Süresi</h2>
            <p className="text-gray-700 dark:text-gray-300">Başarısız aday verileri en fazla 12 ay; uyuşmazlık halinde ilgili zamanaşımı süresi.</p>
          </div>
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">Haklar</h2>
            <p className="text-gray-700 dark:text-gray-300">KVKK 11 kapsamındaki haklar için bize e‑posta ile başvurabilirsiniz.</p>
          </div>
        </div>
      </div>
    </div>
  );
}


