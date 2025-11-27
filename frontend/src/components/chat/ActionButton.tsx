'use client';

import { useRouter } from 'next/navigation';

interface ActionButtonProps {
  text: string;
  action: string;
  data?: Record<string, unknown>;
}

export function ActionButton({ text, action, data }: ActionButtonProps) {
  const router = useRouter();

  const handleClick = () => {
    switch (action) {
      case 'navigate_to_creatives':
        router.push('/creatives');
        break;
      case 'navigate_to_campaigns':
        router.push('/campaigns');
        break;
      case 'navigate_to_reports':
        router.push('/reports');
        break;
      case 'navigate_to_landing_pages':
        router.push('/landing-pages');
        break;
      case 'navigate_to_billing':
        router.push('/billing');
        break;
      case 'create_creative':
        router.push('/creatives/new');
        break;
      case 'create_campaign':
        router.push('/campaigns/new');
        break;
      case 'view_creative':
        if (data?.creative_id) {
          router.push(`/creatives/${data.creative_id}`);
        }
        break;
      case 'view_campaign':
        if (data?.campaign_id) {
          router.push(`/campaigns/${data.campaign_id}`);
        }
        break;
      default:
        console.warn('Unknown action:', action);
    }
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white text-sm font-medium rounded-lg transition-all shadow-sm hover:shadow-md"
    >
      {text}
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </button>
  );
}
