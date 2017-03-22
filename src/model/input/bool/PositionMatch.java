package model.input.bool;

import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionBoolean;
import model.input.GetPosition;

public class PositionMatch extends DecisionBoolean {

	private GetPosition position1;
	private GetPosition position2;

	public PositionMatch(GetPosition position1, GetPosition position2) {
		setPosition1(position1);
		setPosition2(position2);
	}

	public GetPosition getPosition1() {
		return position1;
	}

	public void setPosition1(GetPosition position1) {
		this.position1 = position1;
	}

	public GetPosition getPosition2() {
		return position2;
	}

	public void setPosition2(GetPosition position2) {
		this.position2 = position2;
	}

	@Override
	public boolean decide(Agent agent, Map map) throws Exception {
		XY position1 = getPosition1().getPosition(agent, map);
		XY position2 = getPosition2().getPosition(agent, map);
		if(position1.getX() == position2.getX() && 
				position1.getY() == position2.getY()) {
			return true;
		}
		else {
			return false;
		}
	}
	
	public String toString() {
		String output = Option.HAS_PLANT.toString() + " " + getPosition1().toString() + " " + getPosition2().toString();
		return output;
	}

}
