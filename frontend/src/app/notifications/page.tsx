'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Notification } from '@/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type FilterType = 'all' | 'urgent' | 'important' | 'general';
type FilterReadStatus = 'all' | 'unread' | 'read';

const NOTIFICATION_CATEGORIES = [
  { value: 'all', label: 'All Categories' },
  { value: 'token_expired', label: 'Token Expired' },
  { value: 'ad_rejected', label: 'Ad Rejected' },
  { value: 'credit_low', label: 'Credit Low' },
  { value: 'credit_depleted', label: 'Credit Depleted' },
  { value: 'payment_success', label: 'Payment Success' },
  { value: 'payment_failed', label: 'Payment Failed' },
  { value: 'report_ready', label: 'Report Ready' },
  { value: 'creative_ready', label: 'Creative Ready' },
  { value: 'landing_page_ready', label: 'Landing Page Ready' },
  { value: 'budget_exhausted', label: 'Budget Exhausted' },
  { value: 'ad_paused', label: 'Ad Paused' },
  { value: 'optimization_suggestion', label: 'Optimization Suggestion' },
  { value: 'weekly_summary', label: 'Weekly Summary' },
  { value: 'new_feature', label: 'New Feature' },
  { value: 'system_maintenance', label: 'System Maintenance' },
];

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [filterReadStatus, setFilterReadStatus] = useState<FilterReadStatus>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const pageSize = 20;
  const router = useRouter();

  useEffect(() => {
    fetchNotifications();
  }, [filterType, filterReadStatus, filterCategory, sortOrder, page]);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        limit: pageSize.toString(),
        offset: ((page - 1) * pageSize).toString(),
      });

      if (filterReadStatus === 'unread') {
        params.append('unread_only', 'true');
      }

      const response = await fetch(`/api/v1/notifications?${params}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        let filteredNotifications = data.notifications || [];

        // Apply client-side filters
        if (filterType !== 'all') {
          filteredNotifications = filteredNotifications.filter(
            (n: Notification) => n.type === filterType
          );
        }

        if (filterReadStatus === 'read') {
          filteredNotifications = filteredNotifications.filter((n: Notification) => n.isRead);
        }

        if (filterCategory !== 'all') {
          filteredNotifications = filteredNotifications.filter(
            (n: Notification) => n.category === filterCategory
          );
        }

        // Apply sorting
        filteredNotifications.sort((a: Notification, b: Notification) => {
          const dateA = new Date(a.createdAt).getTime();
          const dateB = new Date(b.createdAt).getTime();
          return sortOrder === 'desc' ? dateB - dateA : dateA - dateB;
        });

        setNotifications(filteredNotifications);
        setTotalCount(data.total || 0);
        setUnreadCount(data.unread_count || 0);
      }
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId: number) => {
    try {
      const response = await fetch(`/api/v1/notifications/${notificationId}/read`, {
        method: 'PUT',
        credentials: 'include',
      });

      if (response.ok) {
        setNotifications(prev =>
          prev.map(n =>
            n.id === notificationId ? { ...n, isRead: true, readAt: new Date().toISOString() } : n
          )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      const response = await fetch('/api/v1/notifications/read-all', {
        method: 'PUT',
        credentials: 'include',
      });

      if (response.ok) {
        setNotifications(prev =>
          prev.map(n => ({ ...n, isRead: true, readAt: new Date().toISOString() }))
        );
        setUnreadCount(0);
      }
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  };

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.isRead) {
      await markAsRead(notification.id);
    }

    if (notification.actionUrl) {
      router.push(notification.actionUrl);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'urgent':
        return '🔴';
      case 'important':
        return '🟡';
      case 'general':
        return '🟢';
      default:
        return '🔵';
    }
  };

  const getNotificationTypeLabel = (type: string) => {
    switch (type) {
      case 'urgent':
        return 'Urgent';
      case 'important':
        return 'Important';
      case 'general':
        return 'General';
      default:
        return type;
    }
  };

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return date.toLocaleDateString();
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
        <p className="mt-2 text-gray-600">
          {unreadCount > 0 ? `You have ${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}` : 'All caught up!'}
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Type filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Type</label>
            <select
              value={filterType}
              onChange={e => {
                setFilterType(e.target.value as FilterType);
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All Types</option>
              <option value="urgent">🔴 Urgent</option>
              <option value="important">🟡 Important</option>
              <option value="general">🟢 General</option>
            </select>
          </div>

          {/* Read status filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
            <select
              value={filterReadStatus}
              onChange={e => {
                setFilterReadStatus(e.target.value as FilterReadStatus);
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="all">All</option>
              <option value="unread">Unread</option>
              <option value="read">Read</option>
            </select>
          </div>

          {/* Category filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
            <select
              value={filterCategory}
              onChange={e => {
                setFilterCategory(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {NOTIFICATION_CATEGORIES.map(cat => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          {/* Sort order */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Sort</label>
            <select
              value={sortOrder}
              onChange={e => setSortOrder(e.target.value as 'desc' | 'asc')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="desc">Newest First</option>
              <option value="asc">Oldest First</option>
            </select>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            Showing {notifications.length} of {totalCount} notifications
          </div>
          {unreadCount > 0 && (
            <Button onClick={markAllAsRead} variant="outline" size="sm">
              Mark All as Read
            </Button>
          )}
        </div>
      </div>

      {/* Notifications list */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <svg
              className="w-16 h-16 mb-4 text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            <p className="text-lg font-medium">No notifications found</p>
            <p className="text-sm mt-1">Try adjusting your filters</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {notifications.map(notification => (
              <button
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                className={`w-full text-left px-6 py-4 hover:bg-gray-50 transition-colors ${
                  !notification.isRead ? 'bg-blue-50' : ''
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Type icon */}
                  <span className="text-2xl flex-shrink-0 mt-1">
                    {getNotificationIcon(notification.type)}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3
                            className={`text-base font-semibold ${
                              !notification.isRead ? 'text-gray-900' : 'text-gray-700'
                            }`}
                          >
                            {notification.title}
                          </h3>
                          {!notification.isRead && (
                            <span className="flex-shrink-0 w-2 h-2 bg-blue-600 rounded-full"></span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mb-2">{notification.message}</p>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <span>{getRelativeTime(notification.createdAt)}</span>
                          <span>•</span>
                          <Badge variant="outline" className="text-xs">
                            {getNotificationTypeLabel(notification.type)}
                          </Badge>
                          {notification.category && (
                            <>
                              <span>•</span>
                              <span className="capitalize">
                                {notification.category.replace(/_/g, ' ')}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Action button */}
                      {notification.actionUrl && notification.actionText && (
                        <Button variant="outline" size="sm" className="flex-shrink-0">
                          {notification.actionText}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200">
            <Button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              variant="outline"
              size="sm"
            >
              Previous
            </Button>
            <span className="text-sm text-gray-600">
              Page {page} of {totalPages}
            </span>
            <Button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              variant="outline"
              size="sm"
            >
              Next
            </Button>
          </div>
        )}
      </div>

      {/* Auto-archive notice */}
      <div className="mt-4 text-sm text-gray-500 text-center">
        Notifications older than 30 days are automatically archived
      </div>
    </div>
  );
}
