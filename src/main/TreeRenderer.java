package main;

import java.awt.Color;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.util.List;

import javax.swing.JFrame;
import javax.swing.JPanel;

import model.Map;
import model.tree.Node;

public class TreeRenderer extends JPanel {
	private static final long serialVersionUID = 1L;
	public static final int POSITION_OFFSET = 7;
	private Node root;
	private JFrame frame;
	
	public TreeRenderer(Map map) {
		super();
		setRoot(map.getPlayers().get(0).getTrees().get(0).getRoot());
		addMouseListener(new MouseAdapter() {
			public void mousePressed(MouseEvent me) {
				System.out.println(me);
				getFrame().repaint();
				
				Renderer renderer = new Renderer(map, map.getMode());
				JFrame frame = new JFrame("WarAgents");
				frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
				frame.add(renderer);
				frame.setSize((map.getWidth() + 2) * Game.SQUARE_SIZE, (map.getHeight() + 3) * Game.SQUARE_SIZE);
				frame.setLocationRelativeTo(null);
				frame.setVisible(true);
				renderer.setFrame(frame);
				
				frame.addWindowListener(new WindowAdapter() {
					  public void windowClosing(WindowEvent e) {
					    System.out.println(ProcessHistory.processHistory(map, map.getPlayers()));
					  }
					});
				System.out.println(map.toString());
				getFrame().dispatchEvent(new WindowEvent(getFrame(), WindowEvent.WINDOW_CLOSING));
			}
		});
	}

	public Node getRoot() {
		return root;
	}

	public void setRoot(Node root) {
		this.root = root;
	}

	public JFrame getFrame() {
		return frame;
	}

	public void setFrame(JFrame frame) {
		this.frame = frame;
	}

	public void positionNode(Node node, int level, List<Node> children, double x, double y, Graphics2D g2d) {
		int levelNodes = node.getTree().getNumberNodes(level);
		double levelDistance = 1;
		drawNode(node, x, y, g2d);
		double sector = 2 * Math.PI / levelNodes;
		double radians = sector / (children.size() * 2);
		double magnitude = Math.sqrt(x * x + y * y);
		double dirX = (x / magnitude);
		double dirY = (y / magnitude);

		if (magnitude == 0.0) {
			dirX = 1.0;
			dirY = 0.0;
		}
		double newX = x + dirX;
		double newY = y + dirY;
		double[] temp = rotate(newX, newY, (-(sector / 2) + radians));
		newX = temp[0];
		newY = temp[1];
		
		for (int i = 0; i < children.size(); i++) {
			positionNode(children.get(i), level + 1, children.get(i).getChildren(), newX, newY, g2d);
			g2d.drawLine(linePos(x), linePos(y), linePos(newX), linePos(newY));
			double[] xy = rotate(newX, newY, (radians * 2));
			newX = xy[0] * levelDistance;
			newY = xy[1] * levelDistance;
		}
	}
	
	private int linePos(double i) {
		double pos = i + POSITION_OFFSET;
		pos = pos * Game.SQUARE_SIZE;
		double mid = pos + (Game.SQUARE_SIZE / 2);
		return (int)mid;
	}

	public double[] rotate(double x, double y, double radians) {
		double ca = Math.cos(radians);
		double sa = Math.sin(radians);
		double newX = ca * x - sa * y;
		double newY = sa * x + ca * y;
		return new double[] { newX, newY };
	}

	public void paintComponent(Graphics g) {
		super.paintComponent(g);
		Graphics2D g2d = (Graphics2D) g;
		Node root = getRoot();
		positionNode(root, root.getHeight(), root.getChildren(), 0, 0, g2d);
	}

	public void drawNode(Node node, double x, double y, Graphics2D g2d) {
		int min = 0;
		int max = node.getTree().getMaxHeight();
		int value = node.getHeight();
		g2d.setColor(new Color(0, getColour(value, min, max), 0));
		x = x + POSITION_OFFSET;
		y = y + POSITION_OFFSET;
		int intX = (int) (x * Game.SQUARE_SIZE);
		int intY = (int)( y * Game.SQUARE_SIZE);
		g2d.fillOval(intX, intY, Game.SQUARE_SIZE, Game.SQUARE_SIZE);
	}

	public int getColour(int value, int min, int max) {
		int range = max - min;
		value += min;
		int colour = (int) ((1.0 * value / range) * 255);
		if (colour > 255) {
			colour = 255;
		}
		return colour;
	}

}
