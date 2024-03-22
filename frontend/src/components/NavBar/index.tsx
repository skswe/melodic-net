import { NavLink } from 'react-router-dom';
import './style.scss';

const NavBar = () => {
  return (
    <div className='navbar'>
      <NavLink className='home' to='/'>
        MelodicNet
      </NavLink>
      <NavLink to='/about'>About</NavLink>
      <NavLink to='/demos'>Demos</NavLink>
    </div>
  );
};
export default NavBar;
