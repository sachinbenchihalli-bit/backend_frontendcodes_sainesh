import React from "react";
import { FiDownload } from "react-icons/fi";
import "./Navbar.scss";

const Navbar = (): JSX.Element => {
    return (
        <div className="navbar">
            <div className="textContent">
                <h1>Command Agent Analytics</h1>
                <p>Monitor and analyze media and marketing chatbot performance</p>
            </div>
            {/* <button className="exportBtn">
                <FiDownload className="icon" />
                Export Data
            </button> */}
        </div>
    );
};

export { Navbar };
