import Link from 'next/link';

export default function CookiesPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg p-8">
          <div className="mb-8">
            <Link href="/" className="text-blue-600 hover:text-blue-800 text-sm">
              ← Back to Home
            </Link>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">Cookie Policy</h1>
          <p className="text-sm text-gray-500 mb-8">Last updated: November 27, 2025</p>

          <div className="prose prose-blue max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. What Are Cookies</h2>
              <p className="text-gray-700 mb-4">
                Cookies are small text files that are placed on your device when you visit our website. They help us provide you with a better experience by remembering your preferences and understanding how you use our Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. How We Use Cookies</h2>
              <p className="text-gray-700 mb-4">
                We use cookies for the following purposes:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Essential Cookies:</strong> Required for the Service to function properly</li>
                <li><strong>Authentication:</strong> To keep you logged in and secure your session</li>
                <li><strong>Preferences:</strong> To remember your settings and preferences</li>
                <li><strong>Analytics:</strong> To understand how you use our Service and improve it</li>
                <li><strong>Performance:</strong> To monitor and improve Service performance</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. Types of Cookies We Use</h2>
              
              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">3.1 Strictly Necessary Cookies</h3>
              <p className="text-gray-700 mb-4">
                These cookies are essential for the Service to function and cannot be disabled:
              </p>
              <div className="overflow-x-auto mb-6">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cookie Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Purpose</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    <tr>
                      <td className="px-4 py-3 text-sm text-gray-900">auth_token</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Authentication and session management</td>
                      <td className="px-4 py-3 text-sm text-gray-700">7 days</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-sm text-gray-900">csrf_token</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Security and CSRF protection</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Session</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">3.2 Functional Cookies</h3>
              <p className="text-gray-700 mb-4">
                These cookies enable enhanced functionality and personalization:
              </p>
              <div className="overflow-x-auto mb-6">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cookie Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Purpose</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    <tr>
                      <td className="px-4 py-3 text-sm text-gray-900">aae_cookie_consent</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Remember your cookie preferences</td>
                      <td className="px-4 py-3 text-sm text-gray-700">1 year</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-sm text-gray-900">user_preferences</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Store your UI preferences and settings</td>
                      <td className="px-4 py-3 text-sm text-gray-700">1 year</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-sm text-gray-900">chat_history</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Save your AI chat conversation history</td>
                      <td className="px-4 py-3 text-sm text-gray-700">30 days</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">3.3 Analytics Cookies</h3>
              <p className="text-gray-700 mb-4">
                These cookies help us understand how visitors interact with our Service:
              </p>
              <div className="overflow-x-auto mb-6">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cookie Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Purpose</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    <tr>
                      <td className="px-4 py-3 text-sm text-gray-900">_ga</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Google Analytics - distinguish users</td>
                      <td className="px-4 py-3 text-sm text-gray-700">2 years</td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 text-sm text-gray-900">_gid</td>
                      <td className="px-4 py-3 text-sm text-gray-700">Google Analytics - distinguish users</td>
                      <td className="px-4 py-3 text-sm text-gray-700">24 hours</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Third-Party Cookies</h2>
              <p className="text-gray-700 mb-4">
                We use services from trusted third parties that may set cookies on your device:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Google OAuth:</strong> For authentication</li>
                <li><strong>Stripe:</strong> For payment processing</li>
                <li><strong>AWS CloudFront:</strong> For content delivery</li>
                <li><strong>Google Analytics:</strong> For usage analytics (if you consent)</li>
              </ul>
              <p className="text-gray-700 mb-4">
                These third parties have their own privacy policies and cookie policies.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Local Storage</h2>
              <p className="text-gray-700 mb-4">
                In addition to cookies, we use browser local storage to:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Store your cookie consent preferences</li>
                <li>Cache data for better performance</li>
                <li>Save your chat conversation history</li>
                <li>Remember your UI preferences</li>
              </ul>
              <p className="text-gray-700 mb-4">
                Local storage data remains on your device until you clear it or delete your account.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Managing Cookies</h2>
              <p className="text-gray-700 mb-4">
                You can control and manage cookies in several ways:
              </p>
              
              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">6.1 Cookie Consent Banner</h3>
              <p className="text-gray-700 mb-4">
                When you first visit our Service, you'll see a cookie consent banner where you can accept or decline non-essential cookies.
              </p>

              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">6.2 Browser Settings</h3>
              <p className="text-gray-700 mb-4">
                Most browsers allow you to:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>View and delete cookies</li>
                <li>Block third-party cookies</li>
                <li>Block all cookies (may affect Service functionality)</li>
                <li>Clear cookies when you close your browser</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">6.3 Browser-Specific Instructions</h3>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Chrome:</strong> Settings → Privacy and security → Cookies and other site data</li>
                <li><strong>Firefox:</strong> Settings → Privacy & Security → Cookies and Site Data</li>
                <li><strong>Safari:</strong> Preferences → Privacy → Manage Website Data</li>
                <li><strong>Edge:</strong> Settings → Cookies and site permissions → Cookies and site data</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Impact of Disabling Cookies</h2>
              <p className="text-gray-700 mb-4">
                If you disable cookies:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>You may not be able to log in or use certain features</li>
                <li>Your preferences will not be saved</li>
                <li>Some pages may not display correctly</li>
                <li>The Service may not function as intended</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Updates to This Policy</h2>
              <p className="text-gray-700 mb-4">
                We may update this Cookie Policy from time to time to reflect changes in our practices or for legal reasons. We will notify you of any material changes by updating the "Last updated" date at the top of this page.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. More Information</h2>
              <p className="text-gray-700 mb-4">
                For more information about how we handle your data, please see our{' '}
                <Link href="/privacy" className="text-blue-600 hover:text-blue-800 underline">
                  Privacy Policy
                </Link>
                .
              </p>
              <p className="text-gray-700 mb-4">
                If you have questions about our use of cookies, please contact us at:
              </p>
              <p className="text-gray-700">
                Email: privacy@aae-platform.com
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
