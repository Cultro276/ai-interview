export function Loader({ label = "Yükleniyor..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-10">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 mx-auto mb-4"></div>
        <p className="text-gray-600 text-sm">{label}</p>
      </div>
    </div>
  );
}


