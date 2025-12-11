import jImagePath from '../assets/johnathanmoon.png'
import rImagePath from '../assets/romereg.png'
import lImagePath from '../assets/snomluis.png'

export function ContactPage() {
    return (
        <div className="container">
            <h2>Contact</h2>
            <div className="contact-person-row">
                <div><h3>Johnathan</h3><br/>
                    <img src={jImagePath} alt="Johnathan Profile Picture" className="contact-img"></img>
                    <p>Name: Johnathan Aye <br></br> Email: johnathan.aye@sjsu.edu</p>
                </div>
                <div><h3>Luis</h3><br/>
                    <img src={lImagePath} alt="Luis Profile Picture" className="contact-img"></img>
                    <p>Name: Luis Adriano <br></br> Email: luis.archundiaadriano@sjsu.edu</p>
                </div>
                <div><h3>Rome</h3><br/>
                    <img src={rImagePath} alt="Rome Profile Picture" className="contact-img"></img>
                    <p>Name: Rome Drori <br></br> Email: rome.drori@sjsu.edu</p>
                </div>

            </div>
        </div>
    );
}