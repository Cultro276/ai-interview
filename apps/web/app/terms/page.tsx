export default function TermsPage() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-800 p-8">
        <h1 className="text-3xl font-bold mb-4">Hizmet Şartları</h1>
        <p className="text-gray-700 dark:text-gray-300 mb-6">Bu sayfa, hizmetin kullanımına ilişkin temel şartları özetler.</p>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">Kullanım</h2>
            <p className="text-gray-700 dark:text-gray-300">Servisi kötüye kullanmamak, güvenlik ve erişim kurallarına uymak esastır.</p>
          </div>
          <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-800">
            <h2 className="text-xl font-semibold mb-2">Sorumluluk</h2>
            <p className="text-gray-700 dark:text-gray-300">Deneme amaçlı sağlanan özellikler değiştirilebilir; bildirim yapılmaksızın güncellenebilir.</p>
          </div>
        </div>
      </div>
    </div>
  );
}


