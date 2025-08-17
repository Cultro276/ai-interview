import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import { Button } from "@/components/ui/Button";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white">
      <MarketingNav active="pricing" />

      {/* Hero Section */}
      <section className="px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <p className="text-blue-600 font-semibold mb-4">PRICING</p>
          <h1 className="mb-6 text-5xl font-bold text-gray-900">
            Pick a plan, start free.
          </h1>
          <p className="mb-12 text-xl text-gray-600 max-w-2xl mx-auto">
            Choose your ideal plan. No obligation, cancel anytime.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            {/* Starter Plan */}
            <div className="p-8 border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <h3 className="text-lg font-bold text-gray-900 mb-2">STARTER</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold text-gray-900">$19</span>
                <span className="text-gray-600">/mo</span>
              </div>
              <p className="text-gray-600 mb-6">What's included:</p>
              <ul className="space-y-3 mb-8">
                <li className="text-gray-600">For individuals</li>
                <li className="text-gray-600">1,000 API Calls/month</li>
                <li className="text-gray-600">Email customer support</li>
                <li className="text-gray-600">Storage 500MB</li>
                <li className="text-gray-600">AI Models: 5/month</li>
              </ul>
              <Button className="w-full" variant="outline">Get Started</Button>
            </div>

            {/* Pro Plan */}
            <div className="p-8 border-2 border-blue-600 rounded-lg shadow-lg relative">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                  POPULAR
                </span>
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">PRO</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold text-gray-900">$29</span>
                <span className="text-gray-600">/mo</span>
              </div>
              <p className="text-gray-600 mb-6">What's included:</p>
              <ul className="space-y-3 mb-8">
                <li className="text-gray-600">2-10 Members</li>
                <li className="text-gray-600">10,000 API Calls/month</li>
                <li className="text-gray-600">Chat customer support</li>
                <li className="text-gray-600">Storage 1GB</li>
                <li className="text-gray-600">AI Models: 15/month</li>
              </ul>
              <Button className="w-full">Get Started</Button>
            </div>

            {/* Team Plan */}
            <div className="p-8 border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <h3 className="text-lg font-bold text-gray-900 mb-2">TEAM</h3>
              <div className="mb-6">
                <span className="text-4xl font-bold text-gray-900">$49</span>
                <span className="text-gray-600">/mo</span>
              </div>
              <p className="text-gray-600 mb-6">What's included:</p>
              <ul className="space-y-3 mb-8">
                <li className="text-gray-600">10+ Members</li>
                <li className="text-gray-600">100,000 API Calls/month</li>
                <li className="text-gray-600">Phone customer support</li>
                <li className="text-gray-600">Storage 5GB</li>
                <li className="text-gray-600">AI Models: 25/month</li>
              </ul>
              <Button className="w-full" variant="outline">Get Started</Button>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">FAQ</h2>
          <h3 className="text-xl font-bold text-gray-900 text-center mb-12">We've got you covered</h3>
          
          <div className="space-y-6">
            <div className="bg-white p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Does this app offer a free trial period?</h4>
              <p className="text-gray-600">
                All individual Framer subscriptions have been grandfathered into a Pro plan at your existing rate. 
                If you were on a Small Team plan, then all 5 seats have been converted over to Pro seats at your existing rate.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">What payment methods do you offer?</h4>
              <p className="text-gray-600">We accept all major credit cards and PayPal for your convenience.</p>
            </div>
            <div className="bg-white p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">How much does a subscription cost?</h4>
              <p className="text-gray-600">Our plans start at $19/month for individuals and scale with your team size and needs.</p>
            </div>
            <div className="bg-white p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">What is your refund policy?</h4>
              <p className="text-gray-600">We offer a 30-day money-back guarantee if you're not satisfied with our service.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-blue-600 font-semibold mb-4">TESTIMONIALS</p>
          <h2 className="text-4xl font-bold text-gray-900 mb-12">Don't take our word for it</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 bg-gray-50 rounded-lg">
              <p className="text-gray-600 mb-4">
                "We struggled to find the right talent globally, but with their automated candidate ranking, we quickly identified top-notch candidates."
              </p>
              <p className="font-semibold text-gray-900">John Smith, HR Manager at ABC Tech Solutions.</p>
            </div>
            <div className="p-6 bg-gray-50 rounded-lg">
              <p className="text-gray-600 mb-4">
                "As a fast-growing startup, we needed an efficient way to find skilled professionals. This AI tool exceeded our expectations."
              </p>
              <p className="font-semibold text-gray-900">Sarah Johnson, CEO of XYZ Innovations.</p>
            </div>
            <div className="p-6 bg-gray-50 rounded-lg">
              <p className="text-gray-600 mb-4">
                "The platform's emphasis on diversity and inclusion impressed me, helping us create a more inclusive workforce."
              </p>
              <p className="font-semibold text-gray-900">Michael Chen, HR Director at Acme Enterprises.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Sales */}
      <section className="px-6 py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto text-center">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Not finding what you're looking for?</h3>
          <Button>Contact Sales</Button>
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