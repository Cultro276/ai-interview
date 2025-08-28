import { productName } from "@/lib/brand";

export function MarketingFooter() {
  return (
    <footer className="px-6 py-16 bg-gray-900 dark:bg-neutral-900 text-white">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          <div>
            <h3 className="text-xl font-bold mb-4">{productName}</h3>
            <p className="text-gray-400">Ön eleme ve işe alım süreçlerinizi önemli ölçüde iyileştirin.</p>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Ürün</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="/solutions">Çözümler</a></li>
              <li><a href="/how-it-works">Nasıl Çalışır</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Kaynaklar</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="/contact">İletişim</a></li>
              <li><a href="/onboarding">Onboarding</a></li>
              <li><a href="/kvkk">KVKK</a></li>
              <li><a href="/privacy">Gizlilik</a></li>
              <li><a href="/faq">SSS</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Şirket</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="/about">Hakkımızda</a></li>
              <li><a href="/about#vizyon">Vizyon & Misyon</a></li>
              <li><a href="/contact">İletişim</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 pt-8 flex justify-between items-center">
          <p className="text-gray-400">{productName} • © {new Date().getFullYear()}</p>
          <div className="flex space-x-4 text-gray-400">
            <a href="/terms" className="hover:text-white">Şartlar</a>
            <a href="/privacy" className="hover:text-white">Gizlilik</a>
          </div>
        </div>
      </div>
    </footer>
  );
}


