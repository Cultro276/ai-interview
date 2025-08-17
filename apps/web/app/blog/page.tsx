import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";

export default function BlogPage() {
  return (
    <div className="min-h-screen bg-white">
      <MarketingNav active="blog" />

      {/* Hero Section */}
      <section className="px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <p className="text-blue-600 font-semibold mb-4">BLOG</p>
          <h1 className="mb-6 text-5xl font-bold text-gray-900">
            Learn and grow
          </h1>
          <p className="mb-12 text-xl text-gray-600 max-w-2xl mx-auto">
            Here are all our essential tips to empower you to embark on your entrepreneurial journey.
          </p>
        </div>
      </section>

      {/* Blog Posts */}
      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Article 1 */}
            <div className="bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <span className="bg-blue-100 text-blue-600 px-3 py-1 rounded-full text-sm font-semibold">ARTICLES</span>
                  <span className="text-gray-500 text-sm ml-auto">5 Nis 2023</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">
                  What is CAC and how do I calculate it?
                </h3>
                <p className="text-gray-600 mb-4">
                  Learn about Customer Acquisition Cost and discover effective strategies to calculate and optimize your CAC for better business growth.
                </p>
                <a href="#" className="text-blue-600 font-semibold hover:text-blue-700">
                  Read more →
                </a>
              </div>
            </div>

            {/* Article 2 */}
            <div className="bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <span className="bg-green-100 text-green-600 px-3 py-1 rounded-full text-sm font-semibold">CASE STUDIES</span>
                  <span className="text-gray-500 text-sm ml-auto">5 Mar 2023</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">
                  How you can use recurring revenue financing for faster growth without dilution
                </h3>
                <p className="text-gray-600 mb-4">
                  Explore alternative financing methods that can accelerate your startup's growth while maintaining equity control.
                </p>
                <a href="#" className="text-blue-600 font-semibold hover:text-blue-700">
                  Read more →
                </a>
              </div>
            </div>

            {/* Article 3 */}
            <div className="bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <span className="bg-purple-100 text-purple-600 px-3 py-1 rounded-full text-sm font-semibold">FUNDING</span>
                  <span className="text-gray-500 text-sm ml-auto">15 Mar 2022</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">
                  Announcing Slang.ai's $20M in funding
                </h3>
                <p className="text-gray-600 mb-4">
                  Major funding announcement and what it means for the future of AI-powered communication solutions.
                </p>
                <a href="#" className="text-blue-600 font-semibold hover:text-blue-700">
                  Read more →
                </a>
              </div>
            </div>

            {/* Article 4 */}
            <div className="bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <span className="bg-orange-100 text-orange-600 px-3 py-1 rounded-full text-sm font-semibold">INNOVATION</span>
                  <span className="text-gray-500 text-sm ml-auto">28 Şub 2022</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">
                  Announcing Slang.ai's $20M in funding
                </h3>
                <p className="text-gray-600 mb-4">
                  Innovation-focused perspective on how funding will drive technological advancement in our platform.
                </p>
                <a href="#" className="text-blue-600 font-semibold hover:text-blue-700">
                  Read more →
                </a>
              </div>
            </div>

            {/* Article 5 */}
            <div className="bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <span className="bg-red-100 text-red-600 px-3 py-1 rounded-full text-sm font-semibold">PRESS RELEASE</span>
                  <span className="text-gray-500 text-sm ml-auto">6 Şub 2022</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">
                  Building a Navigation Component with Variables
                </h3>
                <p className="text-gray-600 mb-4">
                  Technical deep-dive into creating flexible and maintainable navigation components using modern development practices.
                </p>
                <a href="#" className="text-blue-600 font-semibold hover:text-blue-700">
                  Read more →
                </a>
              </div>
            </div>

            {/* Article 6 */}
            <div className="bg-white border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <div className="p-6">
                <div className="flex items-center mb-4">
                  <span className="bg-orange-100 text-orange-600 px-3 py-1 rounded-full text-sm font-semibold">INNOVATION</span>
                  <span className="text-gray-500 text-sm ml-auto">12 Oca 2022</span>
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3">
                  How to Create an Effective Design Portfolio
                </h3>
                <p className="text-gray-600 mb-4">
                  Essential tips and best practices for building a compelling design portfolio that stands out to potential employers.
                </p>
                <a href="#" className="text-blue-600 font-semibold hover:text-blue-700">
                  Read more →
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Newsletter */}
      <section className="px-6 py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Subscribe to our newsletter</h2>
          <p className="text-gray-600 mb-8">
            Stay updated with the latest news, trends, and insights in the world of AI and technology by subscribing to our newsletter.
          </p>
          
          <div className="max-w-md mx-auto">
            <div className="flex flex-col sm:flex-row gap-4">
              <input 
                type="email" 
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                placeholder="Enter your email address"
              />
              <button className="px-6 py-3 text-white bg-blue-600 rounded-lg hover:bg-blue-700 font-semibold">
                Subscribe
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-16 bg-blue-600 text-white text-center">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-4">Make a lasting impression with Hirevision</h2>
          <p className="text-xl mb-8">
            Discover why hiring managers prefer Hirevision over the competition and what makes it the easiest, 
            most powerful video interviewing platform on the market
          </p>
          <button className="px-8 py-3 text-blue-600 bg-white rounded-lg hover:bg-gray-100 font-semibold">
            Duplicate in Framer
          </button>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
} 