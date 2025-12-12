"use client";

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Check, CreditCard, Sparkles } from 'lucide-react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

interface CreditPackageAPI {
  id: string;
  name: string;
  price_cents: number;
  credits: number;
  discount_percent: number;
  description: string;
}

interface CreditPackage {
  id: string;
  name: string;
  price: number;
  credits: number;
  discount: number;
  savings: number;
  unitPrice: number;
  popular?: boolean;
  description: string;
}

export default function RechargePage() {
  const router = useRouter();
  const [packages, setPackages] = useState<CreditPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingPackageId, setProcessingPackageId] = useState<string | null>(null);

  useEffect(() => {
    fetchPackages();
  }, []);

  const fetchPackages = async () => {
    try {
      setLoading(true);
      const response = await api.get<CreditPackageAPI[]>('/credits/packages');

      // Transform API response to frontend format
      const baseUnitPrice = 0.01; // Base price per credit (¥0.01)
      const transformedPackages: CreditPackage[] = response.data.map((pkg, index) => {
        const price = pkg.price_cents / 100; // Convert cents to yuan
        const unitPrice = price / pkg.credits;
        const basePrice = pkg.credits * baseUnitPrice;
        const savings = basePrice - price;

        return {
          id: pkg.id,
          name: pkg.name,
          price,
          credits: pkg.credits,
          discount: pkg.discount_percent,
          savings: savings > 0 ? savings : 0,
          unitPrice,
          popular: index === 1, // Mark second package as popular
          description: pkg.description,
        };
      });

      setPackages(transformedPackages);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load credit packages');
    } finally {
      setLoading(false);
    }
  };

  const handlePurchase = async (packageId: string) => {
    try {
      setProcessingPackageId(packageId);
      
      const successUrl = `${window.location.origin}/billing?payment=success`;
      const cancelUrl = `${window.location.origin}/billing/recharge?payment=cancelled`;
      
      const response = await api.post('/credits/recharge', null, {
        params: {
          package_id: packageId,
          success_url: successUrl,
          cancel_url: cancelUrl,
        }
      });
      
      // Redirect to Stripe checkout
      if (response.data.checkout_url) {
        window.location.href = response.data.checkout_url;
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create checkout session');
      setProcessingPackageId(null);
    }
  };

  const getDiscountBadge = (discount: number) => {
    if (discount === 0) return null;
    
    return (
      <Badge className="bg-green-500 text-white">
        Save {discount}%
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-96 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-6 border-red-200 bg-red-50">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <p>{error}</p>
          </div>
          <Button onClick={fetchPackages} className="mt-4">
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Page Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold">Recharge Credits</h1>
        <p className="text-gray-600">Choose a package that fits your needs. Larger packages offer better discounts!</p>
      </div>

      {/* Packages Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
        {packages.map((pkg) => (
          <Card 
            key={pkg.id}
            className={`relative p-6 hover:shadow-lg transition-shadow ${
              pkg.popular ? 'border-2 border-blue-500' : ''
            }`}
          >
            {/* Popular Badge */}
            {pkg.popular && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <Badge className="bg-blue-500 text-white px-4 py-1">
                  <Sparkles className="w-3 h-3 mr-1 inline" />
                  Most Popular
                </Badge>
              </div>
            )}

            {/* Discount Badge */}
            {pkg.discount > 0 && (
              <div className="absolute top-4 right-4">
                {getDiscountBadge(pkg.discount)}
              </div>
            )}

            {/* Package Info */}
            <div className="space-y-4 mt-2">
              <div>
                <h3 className="text-xl font-bold text-gray-900">{pkg.name}</h3>
                <p className="text-sm text-gray-500 mt-1">{pkg.credits.toLocaleString()} Credits</p>
              </div>

              {/* Price */}
              <div className="space-y-1">
                <div className="flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-gray-900">¥{pkg.price}</span>
                </div>
                <p className="text-sm text-gray-500">
                  ¥{pkg.unitPrice.toFixed(3)} per credit
                </p>
              </div>

              {/* Savings */}
              {pkg.savings > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                  <p className="text-sm font-medium text-green-700">
                    Save ¥{pkg.savings.toFixed(2)}
                  </p>
                </div>
              )}

              {/* Features */}
              <div className="space-y-2 pt-4 border-t">
                <div className="flex items-start gap-2 text-sm">
                  <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-600">Never expires</span>
                </div>
                <div className="flex items-start gap-2 text-sm">
                  <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-600">Use for all AI services</span>
                </div>
                <div className="flex items-start gap-2 text-sm">
                  <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <span className="text-gray-600">Instant activation</span>
                </div>
                {pkg.discount > 0 && (
                  <div className="flex items-start gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-600 font-medium">{pkg.discount}% discount applied</span>
                  </div>
                )}
              </div>

              {/* Purchase Button */}
              <Button
                onClick={() => handlePurchase(pkg.id)}
                disabled={processingPackageId !== null}
                className={`w-full ${
                  pkg.popular 
                    ? 'bg-blue-600 hover:bg-blue-700' 
                    : 'bg-gray-900 hover:bg-gray-800'
                }`}
              >
                {processingPackageId === pkg.id ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    <CreditCard className="w-4 h-4 mr-2" />
                    Purchase Now
                  </>
                )}
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* Payment Info */}
      <Card className="p-6 max-w-3xl mx-auto">
        <h3 className="text-lg font-semibold mb-4">Payment Information</h3>
        <div className="space-y-3 text-sm text-gray-600">
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>Secure payment processing powered by Stripe</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>Credits are added to your account immediately after successful payment</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>All major credit cards and payment methods accepted</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>Need help? Contact support at support@aae.com</p>
          </div>
        </div>
      </Card>

      {/* Back Button */}
      <div className="text-center">
        <Button 
          onClick={() => router.push('/billing')}
          variant="outline"
        >
          Back to Billing
        </Button>
      </div>
    </div>
  );
}
