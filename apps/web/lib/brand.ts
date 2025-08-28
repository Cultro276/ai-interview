// Centralized brand and SEO configuration sourced from environment variables
// Fallbacks keep current behavior until envs are provided

export const siteUrl: string = (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").replace(/\/+$/g, "");

export const companyName: string = process.env.NEXT_PUBLIC_COMPANY_NAME || "Anatolia AI Solutions";
export const productName: string = process.env.NEXT_PUBLIC_PRODUCT_NAME || "RecruiterAI";

export const productDescription: string =
  process.env.NEXT_PUBLIC_PRODUCT_DESCRIPTION ||
  "İK ekipleri için Türkçe yapay zekâ ile video mülakat, otomatik transkript, aday skoru ve rapor. KVKK uyumlu.";

export const twitterHandle: string | undefined = process.env.NEXT_PUBLIC_TWITTER_HANDLE || undefined;
export const logoUrl: string = process.env.NEXT_PUBLIC_LOGO_URL || `${siteUrl}/logo.png`;


