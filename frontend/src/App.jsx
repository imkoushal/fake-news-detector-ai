import Navbar from "./components/Navbar";
import Hero from "./sections/Hero";
import Analyze from "./sections/Analyze";
import Features from "./sections/Features";
import History from "./sections/History";

function App() {
  return (
    <div>
      <Navbar />
      <Hero />
      <Analyze />
      <History />
      <Features />
    </div>
  );
}

export default App;