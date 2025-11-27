'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface EmbeddedChartProps {
  data: any[];
  title?: string;
  type?: 'line' | 'bar' | 'pie';
}

export function EmbeddedChart({ data, title, type = 'line' }: EmbeddedChartProps) {
  if (!data || data.length === 0) {
    return null;
  }

  return (
    <div className="my-3 p-4 bg-white border border-gray-200 rounded-lg">
      {title && (
        <h4 className="text-sm font-semibold text-gray-900 mb-3">{title}</h4>
      )}
      
      <ResponsiveContainer width="100%" height={200}>
        {type === 'line' && (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
            />
            <YAxis 
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
                fontSize: '12px',
              }}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#8b5cf6" 
              strokeWidth={2}
              dot={{ fill: '#8b5cf6', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
