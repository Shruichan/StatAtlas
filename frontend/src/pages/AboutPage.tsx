import { Link } from "react-router-dom";

export function AboutPage() {
    return (
        <div className="container">
            <section>
                <h2>Who</h2>
                Check out our <Link to="/contact">Contact</Link> page.
            </section>

            <section>
                <h2>What</h2>
                StatAtlas summarizes and visualizes key environmental and health data such as pollution burden, walkability, 
                FEMA Risk, and more.
            </section>

            <section>
                <h2>Why</h2>
                StatAtlas wants to inform, educate, and engage the public in a qualitative and 
                quantitative measurement of health, environment, and life of the local area around them. The hope is that those 
                who educate themselves with this information will take action, by sending personal emails with informed statistics
                to support and advocate their representatives.
            </section>

            <section>
                <h2>When</h2>
                StatAtlas was born in the Fall Semester of 2025 and seeks to make a lasting impact on the future.
            </section>

            <section>
                <h2>Where</h2>
                StatAtlas was born in San Jose State University, San Jose, California, United States of America and 
                seeks to expand to a worldwide network of volunteers.
            </section>

            <section>
                <h2>How</h2>
                Our team began with a serious problem and grand vision at hand. Luis on his summer vacation had seen how 
                devastated and polluted natural areas in Mexico were. Coming into the CS152 Programming Paradigms course 
                with Professor Saptarshi Sengupta, he met his friend and former classmate Johnathan. The call for an open-ended
                impactful project was uncertain until Luis remembered what he had seen. Health was brainstormed as another deeply 
                important concern and an interactive map GUI was settled. Rome joined and quickly caught on and with expertise 
                suggested and implemented Quality Of Life and turned gathered data into usable JSON. Now we're here.
            </section>
        </div>
    );
}