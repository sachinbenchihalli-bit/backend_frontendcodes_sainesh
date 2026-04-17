"use client";
import { type User } from "next-auth";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { useEffect, useState } from "react";
import "./NavBar.scss";
import {
  Breadcrumbs,
  CommonDialog,
  CommonMenu,
  ElevaiteIcons,
  type BreadcrumbItem,
  type CommonMenuItem,
} from "@repo/ui/components";

interface NavbarMenuItem {
  label: string;
  onClick: () => void;
}

interface NavBarProps {
  breadcrumbLabels?: Record<string, { label: string; link: string }>;
  hideBreadcrumbs?: boolean;
  customBreadcrumbs?: React.ReactNode;
  user?: User;
  children?: React.ReactNode;
  logOut: () => void;
}

export function NavBar(props: NavBarProps): JSX.Element {
  const pathname = usePathname();
  const [breadcrumbItems, setBreadcrumbItems] = useState<BreadcrumbItem[]>([]);
  const [isLogoutRequestOpen, setIsLogoutRequestOpen] = useState(false);
  const userMenu: CommonMenuItem<NavbarMenuItem>[] = [
    { label: "Logout", onClick: handleLogoutRequest },
  ];

  useEffect(() => {
    setBreadcrumbItems(pathToBreadcrumbs(pathname));
  }, [pathname, props.breadcrumbLabels]);

  function handleLogoutRequest(): void {
    setIsLogoutRequestOpen(true);
  }

  function handleLogout(): void {
    props.logOut();
  }

  function pathToBreadcrumbs(path: string): BreadcrumbItem[] {
    if (!props.breadcrumbLabels) return [];
    if (pathname === "/") return [props.breadcrumbLabels.home];
    const runningPath = path.split("/").filter((str) => str !== "");
    return runningPath.map((str, index) => {
      const breadcrumb: { label: string; link: string } | undefined =
        props.breadcrumbLabels?.[str];
      return {
        label: breadcrumb ? breadcrumb.label : str,
        link:
          index < runningPath.length - 1 && breadcrumb ? breadcrumb.link : "",
      };
    });
  }

  return (
    <div className="adopt-navbar-container">
      {!isLogoutRequestOpen ? undefined : (
        <CommonDialog
          title="Are you sure you want to log out?"
          onConfirm={handleLogout}
          onCancel={() => {
            setIsLogoutRequestOpen(false);
          }}
        />
      )}

      <div className="adopt-navbar-holder">
        <div className="adopt-navbar-left">
          <Link href="/">
            <ElevaiteIcons.SVGNavbarLogo />
          </Link>
          {props.hideBreadcrumbs ? undefined : props.customBreadcrumbs ? (
            props.customBreadcrumbs
          ) : (
            <Breadcrumbs items={breadcrumbItems} />
          )}
        </div>

        <div className="adopt-navbar-right">
          {props.user?.name}

          <CommonMenu<NavbarMenuItem>
            item={undefined}
            menu={userMenu}
            left
            sideCover
            menuIcon={
              <div className="icon-container">
                {!props.user?.image ? (
                  <ElevaiteIcons.SVGUser />
                ) : (
                  <Image
                    alt="User Image"
                    height={40}
                    width={40}
                    src={props.user.image}
                  />
                )}
              </div>
            }
          />
        </div>
      </div>
      {props.children}
    </div>
  );
}
