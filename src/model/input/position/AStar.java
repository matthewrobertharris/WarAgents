package model.input.position;

import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionPosition;
import model.input.GetPosition;

public class AStar extends DecisionPosition {

	private GetPosition position;

	public AStar(GetPosition position) {
		setPosition(position);
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	@Override
	public XY decide(Agent agent, Map map) throws Exception {
		int fromX = agent.getX();
		int fromY = agent.getY();
		int toX = getPosition().getPosition(agent, map).getX();
		int toY = getPosition().getPosition(agent, map).getY();
		
		if(fromX == toX && fromY == toY) {
			return agent.getCurrentPos();
		}
		else {
			int x = fromX - toX;
			int y = fromY - toY;
			if(Math.abs(x) >= Math.abs(y)) {
				if(x > 0) {
					// move left
					return new XY(fromX - 1, fromY);
				}
				else {
					// move right
					return new XY(fromX + 1, fromY);
				}
			}
			else {
				if(y > 0) {
					// move down
					return new XY(fromX, fromY - 1);
				}
				else {
					// move up
					return new XY(fromX, fromY + 1);
				}
			}
		}
	}
	
	public String toString() {
		String output = Option.A_STAR.toString() + " " + getPosition().toString();
		return output;
	}
}
