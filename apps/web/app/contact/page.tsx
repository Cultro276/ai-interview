import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import { Button } from "@/components/ui/Button";

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-white">
      <MarketingNav active="contact" />

      {/* Hero Section */}
      <section className="px-6 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <p className="text-blue-600 font-semibold mb-4">CONTACT</p>
          <h1 className="mb-6 text-5xl font-bold text-gray-900">
            Here to help
          </h1>
          <p className="mb-12 text-xl text-gray-600 max-w-2xl mx-auto">
            Have a question, suggestion, or just want to learn more about our innovative AI-powered hiring solutions? Get in touch!
          </p>
        </div>
      </section>

      {/* Help Options */}
      <section className="px-6 py-16">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Get help quickly</h2>
            <p className="text-gray-600 mb-4">
              Feel free to reach out or access our documentation whenever you need immediate assistance.
            </p>
            <p className="text-gray-600">
              We're here to help and answer any question you might have. We look forward to hearing from you!
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Documentation */}
            <div className="p-8 border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Read the docs</h3>
              <p className="text-gray-600 mb-6">
                Looking for detailed information about our AI-powered hiring solutions and how they can benefit your company? 
                Our comprehensive documentation is available to guide you through the process and answer your questions.
              </p>
              <Button variant="outline">Read documentation</Button>
            </div>

            {/* Support Ticket */}
            <div className="p-8 border border-gray-200 rounded-lg hover:shadow-lg transition-shadow">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Submit a Ticket</h3>
              <p className="text-gray-600 mb-6">
                If you require immediate support or have a specific query, our ticket system is the perfect way to get in touch 
                with our expert team. Submit a ticket, and we'll prioritize your request to provide prompt assistance.
              </p>
              <Button>Open ticket</Button>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Form */}
      <section className="px-6 py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Send us a message</h2>
            <p className="text-gray-600">
              Fill out the form below and we'll get back to you as soon as possible.
            </p>
          </div>

          <div className="bg-white p-8 rounded-lg shadow">
            <form className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">First Name</label>
                  <input 
                    type="text" 
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                    placeholder="Enter your first name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-2">Last Name</label>
                  <input 
                    type="text" 
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                    placeholder="Enter your last name"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">Email</label>
                <input 
                  type="email" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  placeholder="Enter your email address"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">Company</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  placeholder="Enter your company name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">Message</label>
                <textarea 
                  rows={5}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                  placeholder="Tell us about your needs..."
                ></textarea>
              </div>
              
              <Button className="w-full">Send Message</Button>
            </form>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-12">FAQ</h2>
          <h3 className="text-xl font-bold text-gray-900 text-center mb-12">We've got you covered</h3>
          
          <div className="space-y-6">
            <div className="bg-gray-50 p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Does this app offer a free trial period?</h4>
              <p className="text-gray-600">
                All individual Framer subscriptions have been grandfathered into a Pro plan at your existing rate. 
                If you were on a Small Team plan, then all 5 seats have been converted over to Pro seats at your existing rate.
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">What payment methods do you offer?</h4>
              <p className="text-gray-600">We accept all major credit cards and PayPal for your convenience.</p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">How much does a subscription cost?</h4>
              <p className="text-gray-600">Our plans start at $19/month for individuals and scale with your team size and needs.</p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">What is your refund policy?</h4>
              <p className="text-gray-600">We offer a 30-day money-back guarantee if you're not satisfied with our service.</p>
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