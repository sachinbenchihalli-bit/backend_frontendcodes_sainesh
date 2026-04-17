"use client";

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  ArrowLeft, 
  TrendingUp, 
  Zap, 
  ExternalLink,
  Bot,
  Target
} from "lucide-react";
import Link from "next/link";
import { CampaignOptimizationChat } from "../components/CampaignOptimizationChat";

interface Campaign {
  id: string;
  name: string;
  status: string;
  brand?: string;
  budget?: number;
  impressions_delivered?: number;
  clicks?: number;
  ctr?: number;
  roas?: number;
  start_date?: string;
  end_date?: string;
}

export default function CampaignOptimizationPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const campaignId = params.campaignId as string;
  const autoAnalyze = searchParams.get('auto_analyze') === 'true';

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch campaign data with fallback to mock data
  useEffect(() => {
    const fetchCampaign = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`/api/campaigns/${campaignId}`);

        if (!response.ok) {
          // If API fails, use mock data for demo purposes
          console.log('API not available, using mock data for demo');
          const mockCampaign: Campaign = {
            id: campaignId,
            name: `Campaign_${campaignId.substring(0, 8)}`,
            status: 'active',
            brand: 'Demo Brand',
            budget: 15000,
            impressions_delivered: 125000,
            clicks: 2500,
            ctr: 0.02,
            roas: 3.5,
            start_date: '2024-01-15',
            end_date: '2024-02-15'
          };
          setCampaign(mockCampaign);
          setIsLoading(false);
          return;
        }

        const data = await response.json();
        setCampaign(data.data);
      } catch (err) {
        // Fallback to mock data if there's any error
        console.log('Error fetching campaign, using mock data:', err);
        const mockCampaign: Campaign = {
          id: campaignId,
          name: `Demo Campaign ${campaignId.substring(0, 8)}`,
          status: 'active',
          brand: 'Demo Bran',
          budget: 15000,
          impressions_delivered: 125000,
          clicks: 2500,
          ctr: 0.02,
          roas: 3.5,
          start_date: '2024-01-15',
          end_date: '2024-02-15'
        };
        setCampaign(mockCampaign);
      } finally {
        setIsLoading(false);
      }
    };

    if (campaignId) {
      fetchCampaign();
    }
  }, [campaignId]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading campaign data...</p>
        </div>
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Target className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Campaign Not Found</h2>
          <p className="text-gray-600 mb-4">{error || 'The requested campaign could not be found.'}</p>
          <Link href="/campaigns">
            <Button variant="outline">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Campaigns
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/campaigns">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Campaigns
              </Button>
            </Link>
            <div className="h-6 w-px bg-gray-300"></div>
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-pink-500 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {campaign?.status?.toLowerCase() === 'completed' ? 'Campaign Intelligence Assistant' : 'Campaign Intelligence Assistant'}
                </h1>
                <p className="text-sm text-gray-600">
                  {campaign?.status?.toLowerCase() === 'completed' ? 'AI-Powered Campaign Insights and Recommendations' : 'AI-Powered Campaign Insights and Recommendations'}
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            <Link href={`/campaigns/${campaignId}`}>
              <Button variant="outline" size="sm">
                <ExternalLink className="w-4 h-4 mr-2" />
                View Campaign Details
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Campaign Context Card */}
      <div className="px-6 py-4">
        <Card className="bg-white shadow-sm border border-gray-200">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3">
                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="w-6 h-6 text-orange-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h2 className="text-lg font-semibold text-gray-900">{campaign.name}</h2>
                    <Badge
                      variant={campaign.status === 'active' ? 'default' : 'secondary'}
                      className={`${
                        campaign.status === 'active'
                          ? 'bg-green-100 text-green-800 border-green-200'
                          : campaign.status === 'work_in_progress'
                          ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                          : 'bg-gray-100 text-gray-800 border-gray-200'
                      } capitalize`}
                    >
                      {campaign.status === 'work_in_progress' ? 'WIP' : campaign.status}
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">Brand:</span>
                      <div className="font-medium text-gray-900">{campaign.brand || 'N/A'}</div>
                    </div>
                    <div>
                      <span className="text-gray-500">Budget:</span>
                      <div className="font-medium text-gray-900">
                        {campaign.budget ? formatCurrency(campaign.budget) : 'N/A'}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-500">Impressions:</span>
                      <div className="font-medium text-gray-900">
                        {campaign.impressions_delivered?.toLocaleString() || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-500">CTR:</span>
                      <div className="font-medium text-gray-900">
                        {campaign.ctr ? formatPercentage(campaign.ctr) : 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <Zap className="w-5 h-5 text-orange-500" />
                <span className="text-sm font-medium text-orange-600">
                  {campaign?.end_date && new Date(campaign.end_date) < new Date() ? 'Analyzing' : 'Optimizing'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Chat Interface */}
      <div className="px-6 pb-6 flex-1">
        <div className="h-[calc(100vh-340px)]">
          <CampaignOptimizationChat campaign={campaign} autoAnalyze={autoAnalyze} />
        </div>
      </div>
    </div>
  );
}




