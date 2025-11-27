"use client";

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  TooltipProps,
} from 'recharts';
import { Download, ZoomIn, ZoomOut } from 'lucide-react';
import { TrendDataPoint } from '@/types';

interface PerformanceChartsProps {
  trendData: TrendDataPoint[];
  spendByCampaign: { name: string; value: number }[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

export default function PerformanceCharts({ trendData, spendByCampaign }: PerformanceChartsProps) {
  const [visibleLines, setVisibleLines] = useState({
    roas: true,
    cpa: true,
    spend: true,
  });
  const [zoomLevel, setZoomLevel] = useState(1);

  const toggleLine = (line: keyof typeof visibleLines) => {
    setVisibleLines((prev) => ({ ...prev, [line]: !prev[line] }));
  };

  const exportChart = (chartId: string, format: 'png' | 'svg') => {
    // Get the chart element
    const chartElement = document.getElementById(chartId);
    if (!chartElement) return;

    if (format === 'svg') {
      // Export as SVG
      const svgElement = chartElement.querySelector('svg');
      if (!svgElement) return;

      const svgData = new XMLSerializer().serializeToString(svgElement);
      const blob = new Blob([svgData], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${chartId}-${Date.now()}.svg`;
      link.click();
      URL.revokeObjectURL(url);
    } else {
      // Export as PNG
      const svgElement = chartElement.querySelector('svg');
      if (!svgElement) return;

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const svgData = new XMLSerializer().serializeToString(svgElement);
      const img = new Image();
      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(svgBlob);

      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);

        canvas.toBlob((blob) => {
          if (!blob) return;
          const pngUrl = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = pngUrl;
          link.download = `${chartId}-${Date.now()}.png`;
          link.click();
          URL.revokeObjectURL(pngUrl);
        });
      };

      img.src = url;
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const handleDataPointClick = (data: TrendDataPoint) => {
    alert(`Details for ${data.date}:\nSpend: $${data.spend}\nROAS: ${data.roas}x\nCPA: $${data.cpa}`);
  };

  return (
    <div className="space-y-6">
      {/* ROAS Trend Chart */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>7-Day ROAS Trend</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setZoomLevel(Math.max(0.5, zoomLevel - 0.1))}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setZoomLevel(Math.min(2, zoomLevel + 0.1))}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('roas-chart', 'png')}
            >
              <Download className="h-4 w-4 mr-1" />
              PNG
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('roas-chart', 'svg')}
            >
              <Download className="h-4 w-4 mr-1" />
              SVG
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div id="roas-chart" style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top left' }}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={trendData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  onClick={(e) => {
                    if (e.dataKey === 'roas') toggleLine('roas');
                  }}
                  wrapperStyle={{ cursor: 'pointer' }}
                />
                {visibleLines.roas && (
                  <Line
                    type="monotone"
                    dataKey="roas"
                    stroke="#8884d8"
                    strokeWidth={2}
                    dot={{ r: 4, cursor: 'pointer' }}
                    activeDot={{ r: 6, onClick: (_: any, payload: any) => handleDataPointClick(payload.payload) }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* CPA Trend Chart */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>7-Day CPA Trend</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('cpa-chart', 'png')}
            >
              <Download className="h-4 w-4 mr-1" />
              PNG
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('cpa-chart', 'svg')}
            >
              <Download className="h-4 w-4 mr-1" />
              SVG
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div id="cpa-chart">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={trendData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  onClick={(e) => {
                    if (e.dataKey === 'cpa') toggleLine('cpa');
                  }}
                  wrapperStyle={{ cursor: 'pointer' }}
                />
                {visibleLines.cpa && (
                  <Line
                    type="monotone"
                    dataKey="cpa"
                    stroke="#82ca9d"
                    strokeWidth={2}
                    dot={{ r: 4, cursor: 'pointer' }}
                    activeDot={{ r: 6, onClick: (_: any, payload: any) => handleDataPointClick(payload.payload) }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Spend Distribution Pie Chart */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Spend Distribution by Campaign</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('spend-chart', 'png')}
            >
              <Download className="h-4 w-4 mr-1" />
              PNG
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('spend-chart', 'svg')}
            >
              <Download className="h-4 w-4 mr-1" />
              SVG
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div id="spend-chart">
            <ResponsiveContainer width="100%" height={400}>
              <PieChart>
                <Pie
                  data={spendByCampaign}
                  cx="50%"
                  cy="50%"
                  labelLine={true}
                  label={({ name, percent }: any) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                  outerRadius={120}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {spendByCampaign.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Combined Metrics Chart */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Combined Metrics Overview</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('combined-chart', 'png')}
            >
              <Download className="h-4 w-4 mr-1" />
              PNG
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportChart('combined-chart', 'svg')}
            >
              <Download className="h-4 w-4 mr-1" />
              SVG
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div id="combined-chart">
            <ResponsiveContainer width="100%" height={400}>
              <LineChart
                data={trendData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  onClick={(e) => {
                    const key = e.dataKey as keyof typeof visibleLines;
                    if (key in visibleLines) toggleLine(key);
                  }}
                  wrapperStyle={{ cursor: 'pointer' }}
                />
                {visibleLines.spend && (
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="spend"
                    stroke="#FF8042"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                )}
                {visibleLines.roas && (
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="roas"
                    stroke="#8884d8"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                )}
                {visibleLines.cpa && (
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="cpa"
                    stroke="#82ca9d"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
