package model;

public class XY {

	private int x;
	private int y;

	public XY(int x, int y) {
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
	public boolean equals(Object obj) {
		if(this == obj) {
			return true;
		}
		else if(obj instanceof XY) {
			XY xy = (XY)obj;
			return xy.getX() == getX() && xy.getY() == getY();
		}
		else {
			return false;
		}
	}
	
	@Override
	public String toString() {
		String output = "x=" + getX() + " y=" + getY();
		return output;
	}
}
