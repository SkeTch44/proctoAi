import React from "react";
import { FaShield } from "react-icons/fa6";

const Loader = ({ shouldAnimate = true }) => {
  const letters = ["P", "r", "o", "c", "t", "o", "A", "I"];

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center backdrop-blur-md bg-[#dfe4ec] text-[#10B981]">
      {/* Icon */}
      <div className="mb-6 animate-bounce text-4xl text-[#3B82F6]">
        <FaShield />
      </div>

      {/* Falling Letters */}
      <div className="flex space-x-2 text-5xl font-bold">
        {letters.map((char, index) => (
          <span
            key={index}
            className={shouldAnimate ? "inline-block animate-drop" : ""}
            style={shouldAnimate ? { animationDelay: `${index * 0.1}s` } : {}}
          >
            {char}
          </span>
        ))}
      </div>
    </div>
  );
};

export default Loader;
