"use client";
import { SidebarIconObject } from "@repo/ui/components/interfaces";
import { useSession } from "next-auth/react";
import type { ReactNode } from "react";
import { logOut } from "../lib/actions";
import { AppSidebar } from "./AppSidebar";
import { HomeIcon } from "./icons/HomeIcon";
import { CampaignIcon } from "./icons/CampaignIcon";
import { InsertionOrderIcon } from "./icons/InsertionOrderIcon";
import { NavBar } from "./NavBar";
import "./AppLayout.scss";

interface AppLayoutProps {
    children: ReactNode,
    breadcrumbs: Record<string, { label: string; link: string }>;
}

export function AppLayout({ children, breadcrumbs }: AppLayoutProps): JSX.Element {
    const { data: session } = useSession();

    // Define sidebar icons for Adopt Dashboard
    const sidebarIcons: SidebarIconObject[] = [
        {
            icon: <HomeIcon />,
            link: "/",
            description: "Home",
        },
        {
            icon: <InsertionOrderIcon />,
            link: "/insertion-orders",
            description: "Insertion Orders",
        },
        {
            icon: <CampaignIcon />,
            link: "/campaigns",
            description: "Campaigns",
        },
    ];

    return (
        <div className="chatbot-layout-container">
            <NavBar
                breadcrumbLabels={breadcrumbs}
                logOut={logOut}
                user={session?.user}
            />
            <AppSidebar sidebarIcons={sidebarIcons} />
            <div className="main-content">
                {children}
            </div>
        </div>
    );
}
