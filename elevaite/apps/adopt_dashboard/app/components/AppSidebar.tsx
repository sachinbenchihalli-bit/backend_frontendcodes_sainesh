"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React from "react";
import { SidebarIconObject } from "@repo/ui/components";
import "./AppSidebar.scss";

interface AppSidebarProps {
  sidebarIcons: SidebarIconObject[];
}

export function AppSidebar({ sidebarIcons }: AppSidebarProps): JSX.Element {
  return (
    <div className="adopt-sidebar-container">
      <div className="adopt-sidebar-nav">
        <div className="adopt-sidebar-backdrop" />
        {sidebarIcons.map((item) => (
          <SidebarIcon key={item.link} link={item.link} description={item.description}>
            {item.icon}
          </SidebarIcon>
        ))}
      </div>
    </div>
  );
}

export interface SidebarIconProps {
  link: string;
  description?: string;
  children?: React.ReactNode;
}

function SidebarIcon({ children, ...props }: SidebarIconProps): JSX.Element {
  const pathname = usePathname();
  const isActive = (pathname === "/" && props.link === "/") || (pathname !== "/" && props.link !== "/" && pathname.startsWith(props.link));

  const handleClick = (e: React.MouseEvent) => {
    // Prevent navigation if already on the target page
    if (pathname === props.link) {
      e.preventDefault();
    }
  };

  return (
    <Link
      className={[
        "adopt-sidebar-nav-button",
        isActive ? "active" : undefined,
      ].filter(Boolean).join(" ")}
      title={props.description}
      href={props.link}
      onClick={handleClick}
    >
      {children}
    </Link>
  );
}
