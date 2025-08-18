import { MarketingNav } from "@/components/marketing/Nav";
import { MarketingFooter } from "@/components/marketing/Footer";
import { Button } from "@/components/ui/Button";
import { Steps } from "@/components/ui/Steps";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950">
      <MarketingNav active="home" />

      {/* Hero Section */}
      <section className="px-6 py-20 text-center bg-gradient-to-b from-brand-25 to-white dark:from-neutral-900 dark:to-neutral-950 animate-in fade-in-0 slide-in-from-top-2 duration-700">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center px-3 py-1 mb-6 text-sm text-brand-700 bg-brand-100 dark:text-brand-300 dark:bg-brand-700/20 rounded-full">
            <span className="mr-2">🆕</span>
            Create teams in Organisation
          </div>
          <h1 className="mb-6 text-5xl font-bold text-gray-900 dark:text-neutral-100 leading-tight">
            Boost your hiring process with AI solution
          </h1>
          <p className="mb-8 text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Hirevision is used by numerous businesses, institutions, and recruiters to significantly enhance their screening and recruitment procedures.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Button size="lg">Request Demo</Button>
            <Button size="lg" variant="outline">Learn more</Button>
          </div>
          <p className="text-gray-500 dark:text-gray-400 mb-8">Trusted already by 1.2k+</p>
          <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">Already chosen by the world leaders</p>
        </div>
      </section>

      {/* How It Works */}
      <section className="px-6 py-16 bg-gray-50 dark:bg-neutral-900 animate-in fade-in-0 slide-in-from-bottom-2 duration-700">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-brand-700 dark:text-brand-300 font-semibold mb-4">HOW IT WORKS</p>
          <h2 className="text-4xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
            Easy implementation in three easy steps
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-12 max-w-2xl mx-auto">
            Cutting-edge, user-friendly AI tool and growth analytics designed to boost user conversion, engagement, and retention.
          </p>
          <Steps
            current={0}
            steps={["Create a job", "Invite candidates", "Review AI analysis"]}
            className="justify-center"
          />
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-16 animate-in fade-in-0 zoom-in-95 duration-700">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-8 border border-gray-200 dark:border-neutral-800 rounded-lg hover:shadow-lg transition-shadow bg-white dark:bg-neutral-900">
              <p className="text-brand-700 dark:text-brand-300 font-semibold mb-2">FEATURE</p>
              <h3 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                Automated Candidate Ranking
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                Let AI analyze and rank applicants based on qualifications, experience, and skills, ensuring you focus on the most promising candidates first.
              </p>
              <button className="text-brand-700 font-semibold hover:text-brand-600">
                Request demo →
              </button>
            </div>
            
            <div className="p-8 border border-gray-200 dark:border-neutral-800 rounded-lg hover:shadow-lg transition-shadow bg-white dark:bg-neutral-900">
              <p className="text-brand-700 dark:text-brand-300 font-semibold mb-2">FEATURE</p>
              <h3 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                Real-Time Applicant Analytics
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                Get comprehensive insights into candidate performance and interview metrics to make data-driven hiring decisions.
              </p>
              <button className="text-brand-700 font-semibold hover:text-brand-600">
                Request demo →
              </button>
            </div>
            
            <div className="p-8 border border-gray-200 dark:border-neutral-800 rounded-lg hover:shadow-lg transition-shadow bg-white dark:bg-neutral-900">
              <p className="text-brand-700 dark:text-brand-300 font-semibold mb-2">FEATURE</p>
              <h3 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
                Seamless Multilingual Support
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                Conduct interviews in multiple languages with AI-powered translation and analysis capabilities.
              </p>
              <button className="text-brand-700 font-semibold hover:text-brand-600">
                Request demo →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Metrics */}
      <section className="px-6 py-16 bg-gray-50 dark:bg-neutral-900">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-brand-700 dark:text-brand-300 font-semibold mb-4">METRICS</p>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-neutral-100 mb-12">Numbers speaking for themselves</h3>
          <div className="grid md:grid-cols-3 gap-8">
            <div>
              <div className="text-4xl font-bold text-brand-600 mb-2">75%</div>
              <p className="text-gray-600">Candidate match rate</p>
            </div>
            <div>
              <div className="text-4xl font-bold text-brand-600 mb-2">4,000+</div>
              <p className="text-gray-600">Successful placement</p>
            </div>
            <div>
              <div className="text-4xl font-bold text-brand-600 mb-2">50+</div>
              <p className="text-gray-600">Operating countries</p>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="px-6 py-16 bg-white dark:bg-neutral-950">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-brand-700 dark:text-brand-300 font-semibold mb-4">TESTIMONIALS</p>
          <h2 className="text-4xl font-bold text-gray-900 dark:text-neutral-100 mb-12">Don't take our word for it</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 bg-gray-50 dark:bg-neutral-900 rounded-lg">
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                "We struggled to find the right talent globally, but with their automated candidate ranking, we quickly identified top-notch candidates who perfectly fit our requirements."
              </p>
              <p className="font-semibold text-gray-900 dark:text-neutral-100">John Smith, HR Manager at ABC Tech Solutions.</p>
            </div>
            <div className="p-6 bg-gray-50 dark:bg-neutral-900 rounded-lg">
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                "As a fast-growing startup, we needed an efficient way to find skilled professionals from various regions. This AI tool exceeded our expectations."
              </p>
              <p className="font-semibold text-gray-900 dark:text-neutral-100">Sarah Johnson, CEO of XYZ Innovations.</p>
            </div>
            <div className="p-6 bg-gray-50 dark:bg-neutral-900 rounded-lg">
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                "The platform's emphasis on diversity and inclusion impressed me, helping us create a more inclusive workforce."
              </p>
              <p className="font-semibold text-gray-900 dark:text-neutral-100">Michael Chen, HR Director at Acme Enterprises.</p>
            </div>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
} 