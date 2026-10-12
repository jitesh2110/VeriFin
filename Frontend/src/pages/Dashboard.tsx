import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { StatCard } from "@/components/ui/stat-card";
import {
  FileText,
  AlertTriangle,
  Target,
  Users,
  Copy,
  BadgeAlert,
  TrendingUp,
  Upload,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend, Tooltip, Brush } from 'recharts';

interface DashboardStats {
  totalInvoices: number;
  totalVendors: number;
  totalAnomalies: number;
  highSeverityAnomalies: number;
  totalAmountProcessed: number;
}

interface AnomalyCounts {
  duplicates: number;
  invalidGst: number;
  priceAnomalies: number;
}

interface AnomalyTrendData {
  date: string;
  duplicates: number;
  invalidGst: number;
  missingGst: number;
  total: number;
}

interface Activity {
  id: string;
  type: 'upload' | 'verified' | 'anomaly' | 'failed';
  message: string;
  timestamp: string;
  invoiceNo?: string;
  vendor?: string;
}

const Dashboard = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalInvoices: 0,
    totalVendors: 0,
    totalAnomalies: 0,
    highSeverityAnomalies: 0,
    totalAmountProcessed: 0,
  });
  const [anomalyCounts, setAnomalyCounts] = useState<AnomalyCounts>({
    duplicates: 0,
    invalidGst: 0,
    priceAnomalies: 0,
  });
  const [anomalyTrends, setAnomalyTrends] = useState<AnomalyTrendData[]>([]);
  const [recentActivities, setRecentActivities] = useState<Activity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [trendDays, setTrendDays] = useState<number>(30);
  const [customDateRange, setCustomDateRange] = useState({ start: '', end: '' });

  // Load anomaly trends from backend
  const loadAnomalyTrends = async (days: number = trendDays) => {
    try {
      console.log(`Fetching anomaly trends for ${days} days...`);
      const response = await fetch(`http://localhost:8000/api/dashboard/anomaly-trends?days=${days}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Anomaly trends loaded:', data);

      if (data.success && data.trends && data.trends.length > 0) {
        // Format dates for display
        const formattedTrends = data.trends.map((trend: any) => ({
          date: new Date(trend.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          duplicates: trend.duplicates,
          invalidGst: trend.invalidGst || 0,
          missingGst: trend.missingGst || 0,
          total: trend.total,
        }));
        setAnomalyTrends(formattedTrends);
        console.log('Trends set successfully:', formattedTrends.length, 'data points');
      } else {
        console.warn('No trends data, setting empty array');
        setAnomalyTrends([]);
      }
    } catch (error) {
      console.error('Failed to load anomaly trends:', error);
      // Set empty array on error
      setAnomalyTrends([]);
    }
  };

  // Handle filter change
  const handleFilterChange = (days: number) => {
    setTrendDays(days);
    loadAnomalyTrends(days);
  };

  // Load dashboard stats from MongoDB
  useEffect(() => {
    loadDashboardStats();
    loadAnomalyCounts();
    loadRecentActivities();
    loadAnomalyTrends(trendDays);
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      loadDashboardStats();
      loadAnomalyCounts();
      loadRecentActivities();
      loadAnomalyTrends(trendDays); // Refresh with current filter
    }, 30000);
    return () => clearInterval(interval);
  }, [trendDays]); // Re-run when trendDays changes

  const loadDashboardStats = async () => {
    try {
      console.log('Fetching dashboard stats...');
      const response = await fetch('http://localhost:8000/api/dashboard/stats', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Dashboard stats loaded:', data);

      if (data.success && data.stats) {
        setStats(data.stats);
        console.log('Stats set successfully:', data.stats);
      } else {
        console.warn('No stats in response:', data);
        // Set default stats if API returns no data
        setStats({
          totalInvoices: 0,
          totalVendors: 0,
          totalAnomalies: 0,
          highSeverityAnomalies: 0,
          totalAmountProcessed: 0,
        });
      }
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
      // Set default stats on error
      setStats({
        totalInvoices: 0,
        totalVendors: 0,
        totalAnomalies: 0,
        highSeverityAnomalies: 0,
        totalAmountProcessed: 0,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadAnomalyCounts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/anomalies');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Anomaly counts loaded:', data);

      if (data.success && data.anomalies) {
        const counts = {
          duplicates: data.anomalies.filter((a: any) => a.anomalyType === 'DUPLICATE_INVOICE').length,
          invalidGst: data.anomalies.filter((a: any) =>
            a.anomalyType === 'INVALID_GST' ||
            a.anomalyType === 'MISSING_GST' ||
            a.anomalyType === 'GST_VENDOR_MISMATCH'
          ).length,
          priceAnomalies: data.anomalies.filter((a: any) =>
            a.anomalyType === 'UNUSUAL_AMOUNT' ||
            a.anomalyType === 'HSN_PRICE_DEVIATION' ||
            a.anomalyType === 'INVALID_HSN_SAC' ||
            a.anomalyType === 'HSN_GST_RATE_MISMATCH'
          ).length,
        };
        setAnomalyCounts(counts);
      }
    } catch (error) {
      console.error('Failed to load anomaly counts:', error);
    }
  };

  const loadRecentActivities = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/invoices/history?limit=10');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();

      if (data.success && data.invoices) {
        const activities: Activity[] = data.invoices.map((inv: any) => {
          const hasAnomalies = inv.anomalies && inv.anomalies.length > 0;
          const gstVerified = inv.gstVerification && inv.gstVerification[0]?.is_active;

          let type: Activity['type'] = 'upload';
          let message = '';

          if (hasAnomalies) {
            type = 'anomaly';
            message = `Anomaly detected in invoice ${inv.invoiceNumber || inv.invoice_number}`;
          } else if (gstVerified) {
            type = 'verified';
            message = `Invoice ${inv.invoiceNumber || inv.invoice_number} verified successfully`;
          } else if (inv.gstVerification && inv.gstVerification[0]?.success === false) {
            type = 'failed';
            message = `GST verification failed for ${inv.invoiceNumber || inv.invoice_number}`;
          } else {
            type = 'upload';
            message = `New invoice ${inv.invoiceNumber || inv.invoice_number} uploaded`;
          }

          return {
            id: inv._id || inv.id,
            type,
            message,
            timestamp: inv.uploadDate || inv.upload_date || new Date().toISOString(),
            invoiceNo: inv.invoiceNumber || inv.invoice_number,
            vendor: inv.vendorName || inv.vendor_name,
          };
        }).slice(0, 5); // Only show last 5 activities

        setRecentActivities(activities);
      }
    } catch (error) {
      console.error('Failed to load recent activities:', error);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold mb-2">
            Expense Anomaly & Compliance Overview
          </h1>
          <p className="text-muted-foreground">
            Powered by VeriFin — Your Financial Intelligence Agent
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <StatCard
            title="Total Invoices Processed"
            value={isLoading ? "..." : stats.totalInvoices.toLocaleString()}
            icon={FileText}
            trend={{ value: 12.5, isPositive: true }}
          />
          <StatCard
            title="Anomalies Detected"
            value={isLoading ? "..." : stats.totalAnomalies.toString()}
            icon={AlertTriangle}
            variant="warning"
            trend={{ value: stats.highSeverityAnomalies, isPositive: false }}
          />
          <StatCard
            title="Active Vendors"
            value={isLoading ? "..." : stats.totalVendors.toLocaleString()}
            icon={Users}
            trend={{ value: 5.1, isPositive: true }}
          />
        </div>

        {/* Anomaly Distribution & Recent Activity - Side by Side */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Anomaly Trends - Left Side */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">
                Anomaly Trends
              </h3>
              <div className="flex gap-2">
                <Button
                  variant={trendDays === 2 ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleFilterChange(2)}
                >
                  2 Days
                </Button>
                <Button
                  variant={trendDays === 5 ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleFilterChange(5)}
                >
                  5 Days
                </Button>
                <Button
                  variant={trendDays === 7 ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleFilterChange(7)}
                >
                  1 Week
                </Button>
                <Button
                  variant={trendDays === 30 ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleFilterChange(30)}
                >
                  1 Month
                </Button>
                <Button
                  variant={trendDays === 365 ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleFilterChange(365)}
                >
                  All Time
                </Button>
              </div>
            </div>
            {isLoading ? (
              <div className="h-64 flex items-center justify-center">
                <p className="text-muted-foreground">Loading...</p>
              </div>
            ) : anomalyTrends.length === 0 ? (
              <div className="h-64 flex flex-col items-center justify-center text-muted-foreground">
                <TrendingUp className="h-16 w-16 mb-4 opacity-20" />
                <p className="text-sm font-medium">No data available</p>
                <p className="text-xs mt-2">Upload invoices to see anomaly trends</p>
              </div>
            ) : (
              <>
                <div className="flex gap-4 mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className="text-sm text-muted-foreground">Duplicates</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span className="text-sm text-muted-foreground">Invalid GST Number</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                    <span className="text-sm text-muted-foreground">Missing GST Number</span>
                  </div>
                </div>
                {anomalyTrends.every(t => t.total === 0) ? (
                  <div className="relative">
                    <ResponsiveContainer width="100%" height={400}>
                      <LineChart data={anomalyTrends}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 12 }}
                          interval="preserveStartEnd"
                        />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px'
                          }}
                        />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="duplicates"
                          stroke="#ef4444"
                          strokeWidth={2}
                          name="Duplicates"
                          dot={{ fill: '#ef4444', r: 3 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="invalidGst"
                          stroke="#f59e0b"
                          strokeWidth={2}
                          name="Invalid GST Number"
                          dot={{ fill: '#f59e0b', r: 3 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="missingGst"
                          stroke="#a855f7"
                          strokeWidth={2}
                          name="Missing GST Number"
                          dot={{ fill: '#a855f7', r: 3 }}
                        />
                        {anomalyTrends.length > 10 && (
                          <Brush
                            dataKey="date"
                            height={30}
                            stroke="hsl(var(--primary))"
                            fill="hsl(var(--muted))"
                            startIndex={Math.max(0, anomalyTrends.length - 30)}
                          />
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="bg-background/80 backdrop-blur-sm px-4 py-2 rounded-lg border">
                        <p className="text-sm font-medium text-muted-foreground">✅ No anomalies in last {trendDays} {trendDays === 1 ? 'day' : 'days'} - All Clear!</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={anomalyTrends}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12 }}
                        interval="preserveStartEnd"
                      />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px'
                        }}
                      />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="duplicates"
                        stroke="#ef4444"
                        strokeWidth={2}
                        name="Duplicates"
                        dot={{ fill: '#ef4444', r: 3 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="invalidGst"
                        stroke="#f59e0b"
                        strokeWidth={2}
                        name="Invalid GST Number"
                        dot={{ fill: '#f59e0b', r: 3 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="missingGst"
                        stroke="#a855f7"
                        strokeWidth={2}
                        name="Missing GST Number"
                        dot={{ fill: '#a855f7', r: 3 }}
                      />
                      {anomalyTrends.length > 10 && (
                        <Brush
                          dataKey="date"
                          height={30}
                          stroke="hsl(var(--primary))"
                          fill="hsl(var(--muted))"
                          startIndex={Math.max(0, anomalyTrends.length - 30)}
                        />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </>
            )}
          </Card>

          {/* Recent Activity - Right Side */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
            <div className="space-y-3 max-h-[350px] overflow-y-auto">
              {isLoading ? (
                <p className="text-center text-muted-foreground py-4">Loading activities...</p>
              ) : recentActivities.length === 0 ? (
                <p className="text-center text-muted-foreground py-4">No recent activities</p>
              ) : (
                recentActivities.map((activity) => {
                  const getActivityIcon = () => {
                    switch (activity.type) {
                      case 'upload':
                        return <Upload className="h-4 w-4 text-blue-500" />;
                      case 'verified':
                        return <CheckCircle className="h-4 w-4 text-green-500" />;
                      case 'anomaly':
                        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
                      case 'failed':
                        return <XCircle className="h-4 w-4 text-red-500" />;
                      default:
                        return <Clock className="h-4 w-4 text-gray-500" />;
                    }
                  };

                  const getActivityBadge = () => {
                    switch (activity.type) {
                      case 'upload':
                        return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">Uploaded</Badge>;
                      case 'verified':
                        return <Badge variant="default" className="bg-green-50 text-green-700 border-green-200 text-xs">Verified</Badge>;
                      case 'anomaly':
                        return <Badge variant="secondary" className="bg-orange-50 text-orange-700 border-orange-200 text-xs">Anomaly</Badge>;
                      case 'failed':
                        return <Badge variant="destructive" className="bg-red-50 text-red-700 border-red-200 text-xs">Failed</Badge>;
                      default:
                        return <Badge variant="outline" className="text-xs">Unknown</Badge>;
                    }
                  };

                  const formatTime = (timestamp: string) => {
                    const date = new Date(timestamp);
                    const now = new Date();
                    const diffMs = now.getTime() - date.getTime();
                    const diffMins = Math.floor(diffMs / 60000);
                    const diffHours = Math.floor(diffMs / 3600000);
                    const diffDays = Math.floor(diffMs / 86400000);

                    if (diffMins < 1) return 'Just now';
                    if (diffMins < 60) return `${diffMins}m ago`;
                    if (diffHours < 24) return `${diffHours}h ago`;
                    if (diffDays < 7) return `${diffDays}d ago`;
                    return date.toLocaleDateString();
                  };

                  return (
                    <div
                      key={activity.id}
                      className="flex items-start gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors border border-border"
                    >
                      <div className="p-2 rounded-full bg-muted">
                        {getActivityIcon()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs font-medium">{activity.message}</p>
                          {getActivityBadge()}
                        </div>
                        {activity.vendor && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {activity.vendor}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatTime(activity.timestamp)}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>

        {/* Anomaly Categories */}
        <div>
          <h3 className="text-lg font-semibold mb-4">
            Anomaly Categories
          </h3>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="p-6 border-l-4 border-l-destructive hover:shadow-lg transition-all cursor-pointer">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-destructive/10">
                  <Copy className="h-6 w-6 text-destructive" />
                </div>
                <div>
                  <h4 className="font-semibold mb-1">Duplicates Detected</h4>
                  <p className="text-2xl font-bold mb-1">{isLoading ? "..." : anomalyCounts.duplicates}</p>
                  <p className="text-sm text-muted-foreground">
                    Potential duplicate invoices
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6 border-l-4 border-l-warning hover:shadow-lg transition-all cursor-pointer">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-warning/10">
                  <BadgeAlert className="h-6 w-6 text-warning" />
                </div>
                <div>
                  <h4 className="font-semibold mb-1">
                    Invalid GST Numbers
                  </h4>
                  <p className="text-2xl font-bold mb-1">{isLoading ? "..." : anomalyCounts.invalidGst}</p>
                  <p className="text-sm text-muted-foreground">
                    GST verification failed
                  </p>
                </div>
              </div>
            </Card>

            <Card className="p-6 border-l-4 border-l-warning hover:shadow-lg transition-all cursor-pointer">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-warning/10">
                  <TrendingUp className="h-6 w-6 text-warning" />
                </div>
                <div>
                  <h4 className="font-semibold mb-1">HSN/Price Anomalies</h4>
                  <p className="text-2xl font-bold mb-1">{isLoading ? "..." : anomalyCounts.priceAnomalies}</p>
                  <p className="text-sm text-muted-foreground">
                    HSN/SAC & price issues
                  </p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
