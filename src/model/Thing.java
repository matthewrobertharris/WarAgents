package model;

import java.util.ArrayList;
import java.util.List;

public abstract class Thing {

	private String ID;
	private XY currentPos;
	private List<XY> visited;
	
	public Thing(String ID, int x, int y) {
		setID(ID);
		setCurrenPos(new XY(x, y));
		setVisited(new ArrayList<XY>());
		getVisited().add(getCurrentPos());
	}

	public List<XY> getVisited() {
		return visited;
	}

	public void setVisited(List<XY> visited) {
		this.visited = visited;
	}

	public XY getCurrentPos() {
		return currentPos;
	}

	public void setCurrenPos(XY currentPos) {
		this.currentPos = currentPos;
	}

	public String getID() {
		return ID;
	}

	public void setID(String iD) {
		ID = iD;
	}

	public int getX() {
		return getCurrentPos().getX();
	}

	public void setX(int x) {
		getCurrentPos().setX(x);
	}

	public int getY() {
		return getCurrentPos().getY();
	}

	public void setY(int y) {
		getCurrentPos().setY(y);
	}
	
	public void addVisited(XY xy) {
		getVisited().add(xy);
	}

	public String toString() {
		String output = "ID: " + getID();
		output += " x=" + getX() + " y=" + getY();
		return output;
	}
}
