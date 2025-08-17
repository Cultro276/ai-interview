export function MarketingFooter() {
  return (
    <footer className="px-6 py-16 bg-gray-900 text-white">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          <div>
            <h3 className="text-xl font-bold mb-4">Hirevision</h3>
            <p className="text-gray-400">Significantly enhance your screening and recruitment procedures.</p>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Product</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="/">Features</a></li>
              <li><a href="/pricing">Pricing</a></li>
              <li>Use case</li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Resources</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="/blog">Blog</a></li>
              <li>Apps</li>
              <li>Learn</li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-4">Company</h4>
            <ul className="space-y-2 text-gray-400">
              <li>Our Story</li>
              <li>Our Team</li>
              <li><a href="/contact">Contact Us</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-800 pt-8 flex justify-between items-center">
          <p className="text-gray-400">Hirevision • Copyright © {new Date().getFullYear()}</p>
          <div className="flex space-x-4 text-gray-400">
            <span>Terms of service</span>
            <span>Privacy policy</span>
          </div>
        </div>
      </div>
    </footer>
  );
}


