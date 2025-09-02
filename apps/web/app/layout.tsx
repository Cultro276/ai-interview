import './globals.css'
import { Inter } from 'next/font/google'
import Script from 'next/script'
import type { Metadata } from 'next'
import { companyName, productName, productDescription, siteUrl, logoUrl, twitterHandle } from '@/lib/brand'
import { ToastProvider } from "@/context/ToastContext";
import { Toaster } from "@/components/Toaster";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/components/theme/ThemeProvider";

const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' })

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: `${productName} - Yapay Zekâ Mülakat Platformu`,
  description: productDescription,
  applicationName: productName,
  keywords: [
    'yapay zekâ mülakat', 'video mülakat', 'aday skoru', 'mülakat analizi', 'ik yazılımı', 'kvkk', 'insan kaynakları',
  ],
  openGraph: {
    type: 'website',
    url: siteUrl,
    title: `${productName} - Yapay Zekâ Mülakat Platformu`,
    description: productDescription,
    siteName: productName,
    images: [{ url: `${logoUrl}`, width: 1200, height: 630, alt: productName }],
    locale: 'tr_TR',
  },
  twitter: {
    card: 'summary_large_image',
    site: twitterHandle,
    creator: twitterHandle,
    title: `${productName} - Yapay Zekâ Mülakat Platformu`,
    description: productDescription,
    images: [logoUrl],
  },
  robots: {
    index: true,
    follow: true,
  },
  alternates: {
    canonical: '/',
  },
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"></svg>',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body className={`${inter.variable} bg-white dark:bg-neutral-950`}>
        {process.env.NEXT_PUBLIC_GTM_ID ? (
          <>
            <Script id="gtm-loader" strategy="afterInteractive">
              {`(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
              new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
              j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
              'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
              })(window,document,'script','dataLayer','${process.env.NEXT_PUBLIC_GTM_ID}');`}
            </Script>
            <noscript>
              <iframe
                src={`https://www.googletagmanager.com/ns.html?id=${process.env.NEXT_PUBLIC_GTM_ID}`}
                height="0" width="0" style={{ display: 'none', visibility: 'hidden' }}
              />
            </noscript>
          </>
        ) : null}
        {process.env.NEXT_PUBLIC_ANALYTICS_ENABLED === 'true' && !process.env.NEXT_PUBLIC_GTM_ID && process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_ID ? (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_ID}`}
              strategy="afterInteractive"
            />
            <Script id="ga4-init" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);} 
                gtag('js', new Date());
                gtag('config', '${process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_ID}');
              `}
            </Script>
          </>
        ) : null}
        {process.env.NEXT_PUBLIC_ANALYTICS_ENABLED === 'true' && process.env.NEXT_PUBLIC_MIXPANEL_TOKEN ? (
          <>
            <Script src="https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js" strategy="afterInteractive" />
            <Script id="mixpanel-init" strategy="afterInteractive">
              {`
                if (window.mixpanel && window.mixpanel.init) {
                  window.mixpanel.init('${process.env.NEXT_PUBLIC_MIXPANEL_TOKEN}', { debug: false, track_pageview: true });
                }
              `}
            </Script>
          </>
        ) : null}
        {/* JSON-LD Organization & SoftwareApplication */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@graph': [
                {
                  '@type': 'Organization',
                  name: companyName,
                  url: siteUrl,
                  logo: logoUrl,
                  sameAs: [],
                },
                {
                  '@type': 'SoftwareApplication',
                  name: productName,
                  applicationCategory: 'BusinessApplication',
                  operatingSystem: 'Web',
                  description: productDescription,
                  url: siteUrl,
                  offers: {
                    '@type': 'Offer',
                    price: '0',
                    priceCurrency: 'USD',
                  },
                },
              ],
            }),
          }}
        />
        <ThemeProvider>
          <AuthProvider>
            <ToastProvider>
              {children}
              <Toaster />
            </ToastProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
