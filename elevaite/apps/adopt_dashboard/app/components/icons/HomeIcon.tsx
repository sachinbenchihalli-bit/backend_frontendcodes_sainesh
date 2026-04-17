"use client";
import { SVGProps } from "react";

export function HomeIcon(props: SVGProps<SVGSVGElement>): JSX.Element {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="currentColor"
      stroke="none"
      {...props}
    >
      <path d="M12 3c.3 0 .6.1.8.3l7.5 6c.4.3.7.8.7 1.3v9.4c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2v-9.4c0-.5.3-1 .7-1.3l7.5-6c.2-.2.5-.3.8-.3z"></path>
      <rect x="9" y="12" width="6" height="10" rx="1" ry="1" fill="white"></rect>
      <rect x="9" y="14" width="6" height="8" fill="white"></rect>
    </svg>
  );
}
