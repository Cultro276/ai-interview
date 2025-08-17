export default function NotFound() {
  return (
    <div className="min-h-[60vh] grid place-items-center">
      <div className="text-center">
        <h1 className="text-3xl font-semibold text-gray-900">Sayfa bulunamadı</h1>
        <p className="text-gray-600 mt-2">Aradığınız sayfa taşınmış ya da kaldırılmış olabilir.</p>
        <a href="/" className="inline-block mt-4 px-4 py-2 rounded-md bg-brand-600 text-white hover:bg-brand-700">Ana sayfaya dön</a>
      </div>
    </div>
  );
}


