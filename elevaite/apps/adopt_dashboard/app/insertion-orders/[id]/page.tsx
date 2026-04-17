"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  FileText,
  Search,
  Filter,
  ExternalLink,
  ArrowUpRight
} from "lucide-react";
import "../../page.scss";

interface InsertionOrder {
  id: string;
  name: string;
  order_no: string;
  brand?: string;
  status: string;
  budget: number;
  start_date: string;
  end_date: string;
  created_at: string;
  customer_approver: string;
  customer_approver_email: string;
  sales_owner: string;
  sales_owner_email: string;
  fulfillment_owner: string;
  fulfillment_owner_email: string;
  objective_description?: string;
  workspace_type?: string;
  media_plan_url?: string;
  io_pdf_url?: string;
  creative_inspiration_id?: string;
  salesforce_io_id?: string;
}

export default function InsertionOrderDetailsPage() {
  const params = useParams();
  const insertionOrderId = params.id as string;
  
  const [insertionOrder, setInsertionOrder] = useState<InsertionOrder | null>(null);
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch real data from backend API
  useEffect(() => {
    const fetchInsertionOrderData = async () => {
      try {
        setIsLoading(true);

        // Always use API proxy for all environments
        const BACKEND_URL = 'http://localhost:8000';

        // Fetch insertion order details
        const response = await fetch(`${BACKEND_URL}/api/insertion-orders/${insertionOrderId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error('Failed to fetch insertion order');
        }

        const result = await response.json();
        if (!result.success) {
          throw new Error(result.message || 'Failed to fetch insertion order');
        }

        setInsertionOrder(result.data);

        // Fetch associated campaigns
        const campaignsResponse = await fetch(`${BACKEND_URL}/api/insertion-orders/${insertionOrderId}/campaigns`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });

        if (campaignsResponse.ok) {
          const campaignsResult = await campaignsResponse.json();
          if (campaignsResult.success) {
            setCampaigns(campaignsResult.data);
          }
        }

      } catch (error) {
        console.error('Error fetching insertion order data:', error);
        // Set empty data on error
        setInsertionOrder(null);
        setCampaigns([]);
      } finally {
        setIsLoading(false);
      }
    };

    if (insertionOrderId) {
      fetchInsertionOrderData();
    }
  }, [insertionOrderId]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateString: string): string => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const renderSalesforceLink = (salesforceId: string | null | undefined): JSX.Element => {
    if (!salesforceId) {
      return (
        <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200">
          No Link
        </span>
      );
    }

    const salesforceBaseUrl = process.env.NEXT_PUBLIC_SALESFORCE_BASE_URL || 'https://iopextechnologies3-dev-ed.develop.lightning.force.com';
    const salesforceUrl = `${salesforceBaseUrl}/lightning/r/Insertion_Order__c/${salesforceId}/view`;

    return (
      <a
        href={salesforceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-700 border border-blue-200"
        title={`View in Salesforce: ${salesforceId}`}
      >
        <ArrowUpRight className="w-3 h-3 mr-1" />
        Salesforce View
      </a>
    );
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      approved: { label: "Approved", className: "bg-green-100 text-green-800" },
      pending_approval: { label: "Pending Approval", className: "bg-yellow-100 text-yellow-800" },
      "pending approval": { label: "Pending Approval", className: "bg-yellow-100 text-yellow-800" },
      rejected: { label: "Rejected", className: "bg-red-100 text-red-800" },
      draft: { label: "Draft", className: "bg-gray-100 text-gray-800" }
    };

    const normalizedStatus = status.toLowerCase();
    const config = statusConfig[normalizedStatus as keyof typeof statusConfig] || statusConfig.draft;
    return <Badge className={config.className}>{config.label}</Badge>;
  };

  if (isLoading) {
    return (
      <div className="adopt-dashboard-container">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
        </div>
      </div>
    );
  }

  if (!insertionOrder) {
    return (
      <div className="adopt-dashboard-container">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold text-gray-900">Insertion Order not found</h2>
          <p className="text-gray-600 mt-2">The insertion order you're looking for doesn't exist.</p>
        </div>
      </div>
    );
  }

  return (
    <main className="adopt-dashboard-container">
      {/* Header Section */}
      <Card className="bg-white shadow-sm border border-gray-200 mb-6">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-4">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h1 className="text-2xl font-bold text-gray-900">{insertionOrder.name}</h1>
                  {getStatusBadge(insertionOrder.status)}
                </div>
                <p className="text-gray-600 mb-3">{insertionOrder.objective_description || 'No objective description available.'}</p>

                {/* Insertion Order Details - Vertically Stacked */}
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-700">IO Number:</span>
                    <span className="text-blue-600 font-medium">{insertionOrder.order_no}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-700">Brand:</span>
                    <span>{insertionOrder.brand || 'N/A'}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-700">Budget:</span>
                    <span>{formatCurrency(insertionOrder.budget)}</span>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-700">Flight Period:</span>
                    <span>
                      {new Date(insertionOrder.start_date).toLocaleDateString()} - {new Date(insertionOrder.end_date).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 pt-2">
                    {insertionOrder.io_pdf_url && (
                      <a
                        href={insertionOrder.io_pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-700 border border-green-200"
                      >
                        <span>IO PDF</span>
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    )}

                    {insertionOrder.media_plan_url && (
                      <a
                        href={insertionOrder.media_plan_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200"
                      >
                        <span>Media Plan</span>
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    )}

                    {renderSalesforceLink(insertionOrder.salesforce_io_id)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics Cards - Commented out for now
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        Budget Utilization, Active Campaigns, Timeline Progress cards
      </div>
      */}

      {/* Associated Campaigns Section */}
      <Card className="bg-white shadow-sm border border-gray-200">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Associated Campaigns</h2>
            <div className="flex items-center space-x-2">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search campaigns"
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
              </div>
              <Button variant="outline" size="sm">
                <Filter className="w-4 h-4 mr-2" />
                Filter
              </Button>
            </div>
          </div>

          {/* Campaigns Table */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#DEE3ED]">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    Campaign Name
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    Brand
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    Start Date
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    End Date
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                    Performance
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {campaigns.length > 0 ? (
                  campaigns.map((campaign) => (
                    <tr key={campaign.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-blue-600">
                          <a href={`/campaigns/${campaign.id}`}>{campaign.name}</a>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge className={`${
                          campaign.status.toLowerCase() === 'active' ? 'bg-green-100 text-green-800' :
                          campaign.status.toLowerCase() === 'work_in_progress' ? 'bg-yellow-100 text-yellow-800' :
                          campaign.status.toLowerCase() === 'paused' ? 'bg-gray-100 text-gray-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {campaign.status === 'work_in_progress' ? 'WIP' : campaign.status.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {campaign.brand || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(campaign.start_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(campaign.end_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <div>CTR: {campaign.ctr.toFixed(2)}%</div>
                        <div className="text-xs text-gray-500">{campaign.impressions_delivered.toLocaleString()} impressions</div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">
                      No campaigns associated with this insertion order
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
