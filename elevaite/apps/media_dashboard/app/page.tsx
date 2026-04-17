import React from "react";
import { Navbar } from "./components/Navbar.tsx";
import Tabs from "./components/Tabs.tsx";
import "./page.scss";

export default function Home(): JSX.Element {
  return (
    <main style={{
      height: '100vh',
      width: '100vw',
      overflow: 'auto',
      position: 'relative',
      padding: '20px',
      paddingTop: '40px'
      // Adjust based on your navbar height
    }}>
      <Navbar />
      <Tabs />
    </main>
  );
}