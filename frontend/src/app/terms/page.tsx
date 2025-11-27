import Link from 'next/link';

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg p-8">
          <div className="mb-8">
            <Link href="/" className="text-blue-600 hover:text-blue-800 text-sm">
              ← Back to Home
            </Link>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
          <p className="text-sm text-gray-500 mb-8">Last updated: November 27, 2025</p>

          <div className="prose prose-blue max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. Acceptance of Terms</h2>
              <p className="text-gray-700 mb-4">
                By accessing and using the AAE (Automated Ad Engine) Web Platform ("Service"), you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to these Terms of Service, please do not use our Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Description of Service</h2>
              <p className="text-gray-700 mb-4">
                AAE provides an AI-powered advertising platform that helps users create, manage, and optimize advertising campaigns across multiple platforms including Meta, TikTok, and Google Ads.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. User Accounts</h2>
              <p className="text-gray-700 mb-4">
                To use our Service, you must:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Register for an account using Google OAuth authentication</li>
                <li>Provide accurate and complete information</li>
                <li>Maintain the security of your account credentials</li>
                <li>Be at least 18 years old or have parental consent</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Credit System and Billing</h2>
              <p className="text-gray-700 mb-4">
                Our Service operates on a credit-based payment model:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>New users receive 500 credits upon registration</li>
                <li>Credits are used to pay for AI services and premium features</li>
                <li>Credits never expire</li>
                <li>Additional credits can be purchased through our credit packages</li>
                <li>All payments are processed securely through Stripe</li>
                <li>Credits are non-refundable except as required by law</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Ad Account Integration</h2>
              <p className="text-gray-700 mb-4">
                When you connect your advertising accounts (Meta, TikTok, Google):
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>You grant us permission to access and manage your ad accounts on your behalf</li>
                <li>You remain responsible for all advertising costs charged by the platforms</li>
                <li>We store your OAuth tokens securely using encryption</li>
                <li>You can revoke access at any time through your account settings</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Acceptable Use</h2>
              <p className="text-gray-700 mb-4">
                You agree not to:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Use the Service for any illegal or unauthorized purpose</li>
                <li>Violate any laws in your jurisdiction</li>
                <li>Create advertising content that is misleading, fraudulent, or violates platform policies</li>
                <li>Attempt to gain unauthorized access to our systems</li>
                <li>Interfere with or disrupt the Service</li>
                <li>Use automated means to access the Service without permission</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Intellectual Property</h2>
              <p className="text-gray-700 mb-4">
                The Service and its original content, features, and functionality are owned by AAE and are protected by international copyright, trademark, and other intellectual property laws.
              </p>
              <p className="text-gray-700 mb-4">
                Content you create using our Service (creatives, landing pages, etc.) remains your property, but you grant us a license to store, process, and display it as necessary to provide the Service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Data and Privacy</h2>
              <p className="text-gray-700 mb-4">
                Your use of the Service is also governed by our{' '}
                <Link href="/privacy" className="text-blue-600 hover:text-blue-800 underline">
                  Privacy Policy
                </Link>
                . We are committed to protecting your data and complying with GDPR and other applicable data protection laws.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. Termination</h2>
              <p className="text-gray-700 mb-4">
                We may terminate or suspend your account immediately, without prior notice or liability, for any reason, including if you breach these Terms.
              </p>
              <p className="text-gray-700 mb-4">
                You may delete your account at any time through your account settings. Upon deletion, all your data will be permanently removed from our systems within 30 days.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">10. Limitation of Liability</h2>
              <p className="text-gray-700 mb-4">
                To the maximum extent permitted by law, AAE shall not be liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of profits or revenues, whether incurred directly or indirectly, or any loss of data, use, goodwill, or other intangible losses.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">11. Changes to Terms</h2>
              <p className="text-gray-700 mb-4">
                We reserve the right to modify or replace these Terms at any time. We will provide notice of any material changes by posting the new Terms on this page and updating the "Last updated" date.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">12. Contact Us</h2>
              <p className="text-gray-700 mb-4">
                If you have any questions about these Terms, please contact us at:
              </p>
              <p className="text-gray-700">
                Email: legal@aae-platform.com
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
