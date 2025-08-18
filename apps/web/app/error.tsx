"use client";
import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error(error);
  }, [error]);
  return (
    <div className="min-h-[60vh] grid place-items-center">
      <div className="text-center">
        <h1 className="text-3xl font-semibold text-gray-900">Bir şeyler ters gitti</h1>
        <p className="text-gray-600 mt-2">Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.</p>
        <button onClick={reset} className="inline-block mt-4 px-4 py-2 rounded-md bg-brand-600 text-white hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2">Tekrar Dene</button>
      </div>
    </div>
  );
}


