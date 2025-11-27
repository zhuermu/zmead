'use client';

interface ToolInvocation {
  toolCallId: string;
  toolName: string;
  state: 'call' | 'result' | 'error';
  args?: any;
  result?: any;
}

interface ToolInvocationCardProps {
  toolInvocation: ToolInvocation;
}

// Tool name display mapping
const toolDisplayNames: Record<string, string> = {
  create_creative: '生成素材',
  get_creatives: '获取素材列表',
  update_creative: '更新素材',
  delete_creative: '删除素材',
  create_campaign: '创建广告',
  get_campaigns: '获取广告列表',
  update_campaign: '更新广告',
  delete_campaign: '删除广告',
  get_reports: '获取报表',
  analyze_performance: '分析表现',
  create_landing_page: '创建落地页',
  get_landing_pages: '获取落地页列表',
  update_landing_page: '更新落地页',
  get_credit_balance: '查询余额',
  deduct_credit: '扣减积分',
  create_notification: '创建通知',
  get_ad_accounts: '获取广告账户',
};

export function ToolInvocationCard({ toolInvocation }: ToolInvocationCardProps) {
  const { toolName, state, result } = toolInvocation;
  const displayName = toolDisplayNames[toolName] || toolName;

  return (
    <div className="mb-3 ml-0 mr-auto max-w-[85%]">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-center gap-2">
          {state === 'call' && (
            <>
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-blue-700 font-medium">
                正在{displayName}...
              </span>
            </>
          )}

          {state === 'result' && (
            <>
              <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-sm text-green-700 font-medium">
                {displayName}完成
              </span>
            </>
          )}

          {state === 'error' && (
            <>
              <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span className="text-sm text-red-700 font-medium">
                {displayName}失败
              </span>
            </>
          )}
        </div>

        {/* Display result summary */}
        {state === 'result' && result && (
          <div className="mt-2 text-xs text-gray-600">
            {typeof result === 'object' && 'message' in result && (
              <p>{result.message}</p>
            )}
            {typeof result === 'object' && 'count' in result && (
              <p>共 {result.count} 项</p>
            )}
          </div>
        )}

        {/* Display error message */}
        {state === 'error' && result && (
          <div className="mt-2 text-xs text-red-600">
            {typeof result === 'object' && 'error' in result && (
              <p>{result.error}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
