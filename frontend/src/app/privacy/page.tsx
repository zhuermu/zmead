import Link from 'next/link';

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg p-8">
          <div className="mb-8">
            <Link href="/" className="text-blue-600 hover:text-blue-800 text-sm">
              ← Back to Home
            </Link>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
          <p className="text-sm text-gray-500 mb-8">Last updated: November 27, 2025</p>

          <div className="prose prose-blue max-w-none">
            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">1. Introduction</h2>
              <p className="text-gray-700 mb-4">
                AAE ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our Automated Ad Engine Web Platform.
              </p>
              <p className="text-gray-700 mb-4">
                We comply with the General Data Protection Regulation (GDPR) and other applicable data protection laws.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">2. Information We Collect</h2>
              
              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">2.1 Information You Provide</h3>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Account Information:</strong> Email address, display name, profile picture (via Google OAuth)</li>
                <li><strong>Ad Account Credentials:</strong> OAuth tokens for Meta, TikTok, and Google Ads accounts</li>
                <li><strong>Payment Information:</strong> Processed securely through Stripe (we do not store credit card details)</li>
                <li><strong>Content:</strong> Advertising creatives, landing pages, campaign configurations you create</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-900 mb-3 mt-6">2.2 Automatically Collected Information</h3>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Usage Data:</strong> Pages visited, features used, time spent on platform</li>
                <li><strong>Device Information:</strong> Browser type, operating system, IP address</li>
                <li><strong>Cookies:</strong> See our <Link href="/cookies" className="text-blue-600 hover:text-blue-800 underline">Cookie Policy</Link> for details</li>
                <li><strong>Performance Data:</strong> Ad campaign metrics, conversion data, ROI statistics</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">3. How We Use Your Information</h2>
              <p className="text-gray-700 mb-4">
                We use your information to:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Provide and maintain our Service</li>
                <li>Process your transactions and manage your credit balance</li>
                <li>Create and manage advertising campaigns on your behalf</li>
                <li>Generate AI-powered insights and recommendations</li>
                <li>Send you notifications about your account and campaigns</li>
                <li>Improve our Service and develop new features</li>
                <li>Detect and prevent fraud and abuse</li>
                <li>Comply with legal obligations</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">4. Legal Basis for Processing (GDPR)</h2>
              <p className="text-gray-700 mb-4">
                We process your personal data based on:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Contract:</strong> To provide the Service you've signed up for</li>
                <li><strong>Consent:</strong> For marketing communications and optional features</li>
                <li><strong>Legitimate Interests:</strong> To improve our Service and prevent fraud</li>
                <li><strong>Legal Obligation:</strong> To comply with applicable laws and regulations</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">5. Data Sharing and Disclosure</h2>
              <p className="text-gray-700 mb-4">
                We may share your information with:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Advertising Platforms:</strong> Meta, TikTok, Google (to manage your campaigns)</li>
                <li><strong>Payment Processors:</strong> Stripe (to process payments)</li>
                <li><strong>Cloud Services:</strong> AWS (for hosting and storage)</li>
                <li><strong>AI Services:</strong> Google Gemini (for AI-powered features)</li>
                <li><strong>Legal Requirements:</strong> When required by law or to protect our rights</li>
              </ul>
              <p className="text-gray-700 mb-4">
                We do not sell your personal information to third parties.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">6. Data Security</h2>
              <p className="text-gray-700 mb-4">
                We implement appropriate technical and organizational measures to protect your data:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Encryption of data in transit (TLS/SSL) and at rest</li>
                <li>OAuth tokens are encrypted before storage</li>
                <li>Regular security audits and updates</li>
                <li>Access controls and authentication</li>
                <li>Secure cloud infrastructure (AWS)</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">7. Data Retention</h2>
              <p className="text-gray-700 mb-4">
                We retain your data for as long as necessary to provide our Service and comply with legal obligations:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Account Data:</strong> Until you delete your account</li>
                <li><strong>Transaction Records:</strong> 7 years (for tax and accounting purposes)</li>
                <li><strong>Performance Metrics:</strong> 90 days in detail, then archived in summary form</li>
                <li><strong>Deleted Account Data:</strong> Permanently removed within 30 days</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">8. Your Rights (GDPR)</h2>
              <p className="text-gray-700 mb-4">
                Under GDPR, you have the right to:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Access:</strong> Request a copy of your personal data</li>
                <li><strong>Rectification:</strong> Correct inaccurate or incomplete data</li>
                <li><strong>Erasure:</strong> Request deletion of your data ("right to be forgotten")</li>
                <li><strong>Portability:</strong> Receive your data in a machine-readable format</li>
                <li><strong>Restriction:</strong> Limit how we process your data</li>
                <li><strong>Objection:</strong> Object to processing based on legitimate interests</li>
                <li><strong>Withdraw Consent:</strong> Withdraw consent at any time</li>
              </ul>
              <p className="text-gray-700 mb-4">
                To exercise these rights, visit your account settings or contact us at privacy@aae-platform.com
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">9. Data Export and Account Deletion</h2>
              <p className="text-gray-700 mb-4">
                You can:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Export Your Data:</strong> Request a complete export of all your data in ZIP format (available for 24 hours)</li>
                <li><strong>Delete Your Account:</strong> Permanently delete your account and all associated data through your account settings</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">10. International Data Transfers</h2>
              <p className="text-gray-700 mb-4">
                Your data may be transferred to and processed in countries outside your country of residence. We ensure appropriate safeguards are in place, including:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Standard Contractual Clauses (SCCs) approved by the European Commission</li>
                <li>Adequacy decisions for certain countries</li>
                <li>Compliance with applicable data protection frameworks</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">11. Children's Privacy</h2>
              <p className="text-gray-700 mb-4">
                Our Service is not intended for users under 18 years of age. We do not knowingly collect personal information from children. If you believe we have collected information from a child, please contact us immediately.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">12. Changes to This Privacy Policy</h2>
              <p className="text-gray-700 mb-4">
                We may update this Privacy Policy from time to time. We will notify you of any material changes by posting the new Privacy Policy on this page and updating the "Last updated" date.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">13. Contact Us</h2>
              <p className="text-gray-700 mb-4">
                If you have questions about this Privacy Policy or wish to exercise your rights, please contact us:
              </p>
              <p className="text-gray-700 mb-2">
                <strong>Email:</strong> privacy@aae-platform.com
              </p>
              <p className="text-gray-700 mb-2">
                <strong>Data Protection Officer:</strong> dpo@aae-platform.com
              </p>
              <p className="text-gray-700">
                <strong>Address:</strong> [Company Address]
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold text-gray-900 mb-4">14. Supervisory Authority</h2>
              <p className="text-gray-700 mb-4">
                If you are located in the EEA, you have the right to lodge a complaint with your local data protection supervisory authority.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
