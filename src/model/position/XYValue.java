package model.position;

import model.Agent;
import model.Map;
import model.XY;
import model.input.GetPosition;

public class XYValue extends GetPosition {

	private int x;
	private int y;
	
	public XYValue(int x, int y) {
		setX(x);
		setY(y);
	}
	public int getX() {
		return x;
	}

	public void setX(int x) {
		this.x = x;
	}

	public int getY() {
		return y;
	}

	public void setY(int y) {
		this.y = y;
	}

	@Override
	public XY getPosition(Agent agent, Map map) {
		if(inBounds(getX(), getY(), map)) {
			return new XY(getX(), getY());
		}
		else {
			return null;
		}
	}

	public String toString() {
		String output = Position.XY_VALUE.toString();
		return output;
	}
	
}
