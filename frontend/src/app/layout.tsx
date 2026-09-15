import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "./error-handler"; // Import error handler
import { Providers } from "./providers";
import { TooltipProvider } from "@/components/ui/tooltip";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agent Red-Teaming Framework",
  description: "Continuous assurance platform for AI/LLM agent evaluation",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
    apple: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Load error suppressor FIRST - before any other script */}
        <script src="/suppress-web-vitals.js" />
        <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
        <link rel="apple-touch-icon" href="/favicon.svg" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // AGGRESSIVE web vitals error suppression
              (function() {
                // 1. Intercept console.error IMMEDIATELY
                const _consoleError = console.error;
                console.error = function(...args) {
                  const msg = String(args[0] || '');
                  const stack = String(args[1]?.stack || '');
                  if (
                    msg.includes('startTime') || 
                    msg.includes('reportAllChanges') || 
                    msg.includes('<anonymous>:2:') ||
                    msg.includes('VM') ||
                    stack.includes('reportAllChanges')
                  ) {
                    return; // Suppress completely
                  }
                  _consoleError.apply(console, args);
                };

                // 2. Intercept window.onerror
                const _onerror = window.onerror;
                window.onerror = function(msg, url, line, col, error) {
                  const message = String(msg || '');
                  if (message.includes('startTime') || message.includes('reportAllChanges')) {
                    return true; // Suppress
                  }
                  if (_onerror) return _onerror.apply(this, arguments);
                  return false;
                };

                // 3. Intercept addEventListener for 'error'
                const _addEventListener = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                  if (type === 'error') {
                    const wrappedListener = function(event) {
                      if (event.message && (event.message.includes('startTime') || event.message.includes('reportAllChanges'))) {
                        event.preventDefault();
                        event.stopImmediatePropagation();
                        return false;
                      }
                      return listener.apply(this, arguments);
                    };
                    return _addEventListener.call(this, type, wrappedListener, options);
                  }
                  return _addEventListener.call(this, type, listener, options);
                };

                // 4. Wrap requestIdleCallback to catch errors
                if (window.requestIdleCallback) {
                  const _requestIdleCallback = window.requestIdleCallback;
                  window.requestIdleCallback = function(callback, options) {
                    const wrappedCallback = function(deadline) {
                      try {
                        return callback(deadline);
                      } catch (e) {
                        const error = String(e);
                        if (!error.includes('startTime') && !error.includes('reportAllChanges')) {
                          throw e;
                        }
                        // Suppress web vitals errors
                      }
                    };
                    return _requestIdleCallback.call(this, wrappedCallback, options);
                  };
                }
              })();
            `,
          }}
        />
      </head>
      <body className={`${inter.className} antialiased`}>
        <Providers>
          <TooltipProvider>{children}</TooltipProvider>
        </Providers>
      </body>
    </html>
  );
}