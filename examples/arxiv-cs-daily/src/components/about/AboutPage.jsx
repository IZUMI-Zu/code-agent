
import './AboutPage.css';

const AboutPage = () => {
  return (
    <div className="about-page">
      <h1>About arXiv CS Daily</h1>
      <p className="lead">Your daily source for the latest computer science research papers.</p>
      
      <div className="about-content">
        <section className="about-section">
          <h2>Our Mission</h2>
          <p>
            arXiv CS Daily aims to make cutting-edge computer science research more accessible to 
            researchers, students, and enthusiasts. We curate and present the latest papers from 
            arXiv.org in a clean, easy-to-browse interface.
          </p>
        </section>
        
        <section className="about-section">
          <h2>What is arXiv?</h2>
          <p>
            arXiv is a free distribution service and an open archive for scholarly articles in 
            the fields of physics, mathematics, computer science, quantitative biology, 
            quantitative finance, statistics, electrical engineering and systems science, and economics.
          </p>
        </section>
        
        <section className="about-section">
          <h2>Contact Us</h2>
          <p>
            Have questions or feedback? Reach out to us at{' '}
            <a href="mailto:contact@arxicsdaily.com">contact@arxicsdaily.com</a>
          </p>
        </section>
      </div>
    </div>
  );
};

export default AboutPage;
